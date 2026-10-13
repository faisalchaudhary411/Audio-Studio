"""
api_keys.py — VoxCraft's developer API product: a separate, metered paid
plan (distinct from the Pro/Pro+ browser app licenses in licensing.py)
that lets a customer call VoxCraft's TTS engine programmatically.

Design decisions, and why:

- FIXED MONTHLY CHARACTER ALLOWANCE, not real-time pay-per-character
  billing. True usage-based billing (like ElevenLabs' overage charges)
  needs a payment gateway that supports metered billing — Freemius
  (fixed-price subscriptions) and manual PKR transfers don't. A customer
  buys a plan with a monthly character quota through the SAME payment
  flow already built for Pro/Pro+, and the admin issues a key once payment
  is confirmed. Self-serve signup/billing can be added later without
  changing this module's core mechanics.

- KEYS ARE HASHED AT REST, never stored raw. Same principle as a
  password: even a full database leak doesn't hand out working keys. The
  raw key is shown to the admin exactly once, at creation time, for
  copying into the email sent to the customer.

- QUOTA STATE lives in a SEPARATE table (persistence.api_key_usage) from
  key metadata (persistence.api_keys), using a real atomic transaction
  (persistence.api_key_usage_transaction) rather than the simpler
  whole-table pattern used for rarely-edited things like blog posts. This
  app runs 2 gunicorn worker processes — see usage_tracking.py's
  docstring for the full history of a near-identical bug that silently
  under-enforced browser usage limits before it was fixed the same way.
  Proven correct here with an actual concurrency stress test (20 threads
  bumping one key's counter simultaneously landed on the exact expected
  total, not less) before this module was built on top of it.

- WHOLESALE / RESELLER KEYS (plan "api_wholesale", or any plan with the
  optional fields below). Every field is optional and defaults to the old
  behaviour, so existing keys keep working untouched:
    billing_mode           "monthly" (default; quota resets each month) or
                           "prepaid" (a character balance that does NOT
                           reset, topped up by the admin after payment).
    rpm_limit              requests per minute per key (0 = unlimited).
    max_chars_per_request  per-key override of the global per-request cap.
    allowed_voices         list of voice_ids this key may use (empty = all).
    notes                  free-text admin note (contract, invoice refs).
  All counters (usage, balance, rate window, daily history) live in the
  SAME api_key_usage row as the monthly counter, so every update stays
  inside one atomic SQLite transaction.
"""
import hashlib
import secrets
import datetime as dt

import persistence

KEY_PREFIX = "vox_live_"

BILLING_MONTHLY = "monthly"
BILLING_PREPAID = "prepaid"
DAILY_HISTORY_DAYS = 62          # how many days of per-day usage to keep per key
MAX_CHARS_PER_REQUEST_CEILING = 20000


def _current_period() -> str:
    return dt.datetime.now().strftime("%Y-%m")


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_raw_key() -> str:
    """vox_live_ + 32 URL-safe random characters — same shape as Stripe/
    OpenAI/ElevenLabs style keys, immediately recognizable as a VoxCraft
    key if it ever shows up somewhere it shouldn't (a public repo, a log
    file), which makes accidental-leak scanning easier for the customer
    and for us."""
    return KEY_PREFIX + secrets.token_urlsafe(24)


def normalize_voice_list(raw) -> list:
    """Accepts a list, or a comma/space/newline-separated string, and returns
    a clean de-duplicated list of voice_ids. Empty list means "all voices"."""
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.replace("\n", ",").replace(" ", ",").split(",")
    seen, out = set(), []
    for v in raw:
        v = str(v).strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _clean_limits(billing_mode=None, rpm_limit=None, max_chars_per_request=None,
                  allowed_voices=None, notes=None) -> dict:
    """Validates/clamps the optional wholesale fields. Only keys that were
    actually provided (not None) are returned, so the same helper serves both
    creation (fill defaults around it) and later edits (touch only what
    changed)."""
    out = {}
    if billing_mode is not None:
        out["billing_mode"] = BILLING_PREPAID if billing_mode == BILLING_PREPAID else BILLING_MONTHLY
    if rpm_limit is not None:
        out["rpm_limit"] = max(0, min(int(rpm_limit), 100000))
    if max_chars_per_request is not None:
        n = int(max_chars_per_request)
        out["max_chars_per_request"] = 0 if n <= 0 else max(100, min(n, MAX_CHARS_PER_REQUEST_CEILING))
    if allowed_voices is not None:
        out["allowed_voices"] = normalize_voice_list(allowed_voices)
    if notes is not None:
        out["notes"] = str(notes).strip()[:500]
    return out


def create_api_key(customer_name: str, customer_email: str, plan: str, monthly_char_quota: int,
                    freemius_license_id: str = None, *, billing_mode: str = None,
                    rpm_limit: int = None, max_chars_per_request: int = None,
                    allowed_voices=None, notes: str = None) -> dict:
    """Creates the key record and returns {"raw_key": ..., "record": {...}}.
    raw_key is ONLY available here, at creation — store it now (the admin
    panel shows it once, in a copy-friendly box) because it can never be
    retrieved again, only re-hashed-and-compared against a new guess.

    freemius_license_id links this key back to a paid Freemius subscription
    when the key was auto-issued via /fs-callback/api rather than created
    manually in admin — lets the webhook find and revoke/restore the right
    key on cancellation/renewal, same idea as licensing.py's app licenses."""
    raw_key = generate_raw_key()
    key_hash = hash_key(raw_key)
    record = {
        "id": str(int(dt.datetime.now().timestamp() * 1000)),
        "key_hash": key_hash,
        "key_prefix": raw_key[:len(KEY_PREFIX) + 6],  # e.g. "vox_live_AbCdEf" — enough to recognize, not enough to guess
        "customer_name": customer_name,
        "customer_email": customer_email,
        "plan": plan,
        "monthly_char_quota": monthly_char_quota,
        "active": True,
        "created": dt.datetime.now().strftime("%Y-%m-%d"),
        "freemius_license_id": freemius_license_id or "",
        # Wholesale fields — defaults reproduce the pre-existing behaviour.
        "billing_mode": BILLING_MONTHLY,
        "rpm_limit": 0,
        "max_chars_per_request": 0,
        "allowed_voices": [],
        "notes": "",
    }
    record.update(_clean_limits(billing_mode, rpm_limit, max_chars_per_request,
                                allowed_voices, notes))
    keys = persistence.load_api_keys()
    keys.insert(0, record)
    persistence.save_api_keys(keys)
    return {"raw_key": raw_key, "record": record}


def find_key_by_email(customer_email: str, plan: str = None):
    """Used by the free self-serve signup to avoid silently minting a new
    key (and burning a fresh free quota) every time the same person
    re-submits the form — reuses/reports the existing one instead."""
    email = (customer_email or "").strip().lower()
    for record in persistence.load_api_keys():
        if record.get("customer_email", "").strip().lower() == email:
            if plan is None or record.get("plan") == plan:
                return record
    return None


def find_keys_by_email(customer_email: str) -> list:
    """All keys on file for this email (active or revoked), newest first —
    used by the /account dashboard, unlike find_key_by_email above which
    only needs the first match for signup dedup. A customer normally has
    one, but rotate_key() below leaves the old one revoked-not-deleted, so
    someone who's rotated has a short history here rather than an active
    key silently disappearing from their own view."""
    email = (customer_email or "").strip().lower()
    return [r for r in persistence.load_api_keys()
            if r.get("customer_email", "").strip().lower() == email]


def rotate_key(key_id: str) -> dict:
    """Customer-initiated (from /account) or admin-initiated key rotation:
    revokes the old key and mints a fresh one with the same customer/plan/
    quota, so a compromised or lost key can be replaced without emailing
    Faisal. Returns {} if key_id doesn't exist, else {"raw_key":...,
    "record": {...}} same shape as create_api_key — this is also a raw-key
    moment, shown/emailed once, same rule as creation."""
    keys = persistence.load_api_keys()
    old = next((k for k in keys if str(k["id"]) == str(key_id)), None)
    if not old:
        return {}
    revoke_key(key_id)
    result = create_api_key(
        old["customer_name"], old["customer_email"], old["plan"], old["monthly_char_quota"],
        billing_mode=old.get("billing_mode"), rpm_limit=old.get("rpm_limit"),
        max_chars_per_request=old.get("max_chars_per_request"),
        allowed_voices=old.get("allowed_voices"), notes=old.get("notes"))
    # Usage + prepaid balance are keyed by key HASH, so without this a
    # rotation silently reset the month's usage to zero (free quota reset
    # for anyone who rotated) and wiped a prepaid balance. Carry it over.
    _copy_usage(old["key_hash"], result["record"]["key_hash"])
    return result


def find_key_by_freemius_id(freemius_license_id: str):
    if not freemius_license_id:
        return None
    for record in persistence.load_api_keys():
        if record.get("freemius_license_id") == freemius_license_id:
            return record
    return None


def sync_key_from_freemius_event(freemius_license_id: str, event_type: str) -> dict:
    """Mirrors licensing.sync_license_from_freemius_event for API keys —
    called from the same /webhook/freemius handler so a cancelled or
    expired paid API subscription stops working automatically instead of
    quietly staying active forever, and a recovered renewal (dunning
    retry succeeds) un-revokes it again. A no-op, not an error, when the
    event is for a browser Pro license rather than an API key (most
    webhook events will be) — the two products share one Freemius
    product/webhook but are looked up independently."""
    record = find_key_by_freemius_id(freemius_license_id)
    if not record:
        return {"success": False, "reason": "not_an_api_key"}
    if event_type == "license.extended":
        unrevoke_key(record["id"])
        return {"success": True, "action": "unrevoked", "key_id": record["id"]}
    if event_type in ("license.cancelled", "license.expired"):
        revoke_key(record["id"])
        return {"success": True, "action": "revoked", "key_id": record["id"]}
    return {"success": False, "reason": "ignored_event"}


def find_key_record(raw_key: str):
    """Looks up a key record by hashing the provided raw key and matching
    against stored hashes — O(n) over all keys, which is fine at the scale
    this is designed for (a manually-issued, low-volume product, not a
    self-serve product with thousands of keys). If this ever needs to
    scale further, key_hash should become an indexed column instead of
    living inside the JSON blob."""
    if not raw_key or not raw_key.startswith(KEY_PREFIX):
        return None
    target_hash = hash_key(raw_key)
    for record in persistence.load_api_keys():
        if record.get("key_hash") == target_hash:
            return record
    return None


def _today() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def _roll_period(usage: dict, period: str) -> dict:
    """Returns a usage dict normalised for `period`: monthly counters reset on
    rollover, but the prepaid balance, daily history and top-up log survive —
    "balance" must never reset just because the calendar flipped."""
    usage = dict(usage or {})
    if usage.get("period") != period:
        usage["period"] = period
        usage["chars_used"] = 0
        usage["requests"] = 0
    usage.setdefault("chars_used", 0)
    usage.setdefault("requests", 0)
    usage.setdefault("balance", 0)
    return usage


def get_usage(key_hash: str) -> dict:
    """Read-only usage snapshot for the CURRENT period — resets the
    displayed character count to 0 once the period rolls over, without
    needing a separate cleanup job. last_used, balance and daily history are
    preserved across the period boundary regardless."""
    return _roll_period(persistence.peek_api_key_usage(key_hash), _current_period())


def is_prepaid(record: dict) -> bool:
    return record.get("billing_mode") == BILLING_PREPAID


def remaining_chars(record: dict, usage: dict = None) -> int:
    """Characters this key can still use: the prepaid balance for prepaid
    keys, otherwise what's left of this month's quota."""
    usage = usage if usage is not None else get_usage(record["key_hash"])
    if is_prepaid(record):
        return max(0, int(usage.get("balance", 0)))
    return max(0, int(record["monthly_char_quota"]) - int(usage.get("chars_used", 0)))


def would_exceed_quota(record: dict, char_count: int) -> bool:
    """Read-only check — call BEFORE doing the actual generation work, so
    a request that's going to be rejected never touches the TTS engine.
    (Check-then-bump leaves a tiny overshoot window equal to the key's
    in-flight concurrent requests; the prepaid balance is clamped at 0 so it
    can never go negative.)"""
    return char_count > remaining_chars(record)


def voice_allowed(record: dict, voice_id: str) -> bool:
    allowed = record.get("allowed_voices") or []
    return (not allowed) or voice_id in allowed


def effective_max_chars(record: dict, default: int) -> int:
    n = int(record.get("max_chars_per_request") or 0)
    return n if n > 0 else default


def check_rate_limit(record: dict) -> tuple:
    """Per-key requests-per-minute limit using a fixed one-minute window held
    in the same atomic usage row (so it is correct across gunicorn workers).
    Returns (allowed, retry_after_seconds, remaining_in_window). A no-op
    (and no DB write) for keys with rpm_limit == 0."""
    limit = int(record.get("rpm_limit") or 0)
    if limit <= 0:
        return True, 0, -1
    now = dt.datetime.now()
    window = now.strftime("%Y-%m-%d %H:%M")
    with persistence.api_key_usage_transaction(record["key_hash"]) as holder:
        usage = _roll_period(holder["usage"], _current_period())
        rate = usage.get("rate") or {}
        if rate.get("w") != window:
            rate = {"w": window, "n": 0}
        if rate["n"] >= limit:
            holder["usage"] = usage
            return False, max(1, 60 - now.second), 0
        rate["n"] += 1
        usage["rate"] = rate
        holder["usage"] = usage
        return True, 0, limit - rate["n"]


def bump_usage(key_hash: str, char_count: int, prepaid: bool = False):
    """Only call AFTER a generation actually succeeds — mirrors
    app.py's _bump_monthly_chars() pattern for the browser-based free
    tier, for the same reason (a failed generation, e.g. a TTS engine
    error, should never consume quota the customer is paying for).

    Also stamps last_used, the request counter, per-day history (for the
    partner's usage report / reconciliation) and, for prepaid keys, deducts
    the balance — all in the SAME atomic transaction, rather than as
    separate writes that could race."""
    period = _current_period()
    today = _today()
    with persistence.api_key_usage_transaction(key_hash) as holder:
        usage = _roll_period(holder["usage"], period)
        usage["chars_used"] += char_count
        usage["requests"] += 1
        usage["last_used"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        if prepaid:
            usage["balance"] = max(0, int(usage.get("balance", 0)) - char_count)
        daily = usage.get("daily") or {}
        day = daily.get(today) or {"chars": 0, "requests": 0}
        day["chars"] += char_count
        day["requests"] += 1
        daily[today] = day
        if len(daily) > DAILY_HISTORY_DAYS:
            for old_day in sorted(daily)[:len(daily) - DAILY_HISTORY_DAYS]:
                daily.pop(old_day, None)
        usage["daily"] = daily
        holder["usage"] = usage


def top_up_balance(key_hash: str, chars: int) -> int:
    """Admin action after receiving a prepayment: adds `chars` to a prepaid
    key's balance (atomic) and logs it. Returns the new balance."""
    chars = int(chars)
    if chars <= 0:
        raise ValueError("top-up must be a positive number of characters")
    with persistence.api_key_usage_transaction(key_hash) as holder:
        usage = _roll_period(holder["usage"], _current_period())
        usage["balance"] = int(usage.get("balance", 0)) + chars
        log = usage.get("topups") or []
        log.append({"date": _today(), "chars": chars})
        usage["topups"] = log[-20:]
        holder["usage"] = usage
        return usage["balance"]


def _copy_usage(old_hash: str, new_hash: str):
    """Copies the whole usage row (monthly counter, balance, history) from an
    old key hash to its rotated replacement."""
    old = persistence.peek_api_key_usage(old_hash)
    if not old:
        return
    with persistence.api_key_usage_transaction(new_hash) as holder:
        holder["usage"] = dict(old)


def usage_report(record: dict, days: int = 31) -> dict:
    """What a partner sees at GET /api/v1/usage: where they stand and a
    per-day history they can reconcile against their own invoices."""
    usage = get_usage(record["key_hash"])
    daily = usage.get("daily") or {}
    history = [{"date": d, "characters": daily[d]["chars"], "requests": daily[d]["requests"]}
               for d in sorted(daily)[-days:]]
    report = {
        "plan": record.get("plan"),
        "billing_mode": record.get("billing_mode") or BILLING_MONTHLY,
        "period": usage["period"],
        "characters_used_this_period": usage["chars_used"],
        "requests_this_period": usage["requests"],
        "characters_remaining": remaining_chars(record, usage),
        "rpm_limit": int(record.get("rpm_limit") or 0) or None,
        "max_characters_per_request": effective_max_chars(record, 0) or None,
        "allowed_voices": record.get("allowed_voices") or "all",
        "last_used": usage.get("last_used"),
        "daily": history,
    }
    if is_prepaid(record):
        report["prepaid_balance"] = max(0, int(usage.get("balance", 0)))
    else:
        report["monthly_quota"] = int(record["monthly_char_quota"])
    return report


def update_key_settings(key_id: str, *, monthly_char_quota: int = None, **limits) -> bool:
    """Admin edit of an existing key's limits (rate limit, per-request cap,
    voice allowlist, billing mode, notes, monthly quota). Only the fields
    passed are changed. Returns True when the key was found and saved."""
    keys = persistence.load_api_keys()
    for k in keys:
        if str(k["id"]) == str(key_id):
            if monthly_char_quota is not None:
                k["monthly_char_quota"] = max(1, int(monthly_char_quota))
            k.update(_clean_limits(**limits))
            ok, _err = persistence.save_api_keys(keys)
            return bool(ok)
    return False


def revoke_key(key_id: str) -> bool:
    keys = persistence.load_api_keys()
    for k in keys:
        if str(k["id"]) == str(key_id):
            k["active"] = False
            ok, _err = persistence.save_api_keys(keys)
            return bool(ok)
    return False


def unrevoke_key(key_id: str) -> bool:
    """Reactivate a previously revoked API key. Returns True only when the
    key was found AND the write succeeded — callers (admin UI) can surface
    a failure instead of silently appearing to do nothing."""
    keys = persistence.load_api_keys()
    for k in keys:
        if str(k["id"]) == str(key_id):
            k["active"] = True
            ok, _err = persistence.save_api_keys(keys)
            return bool(ok)
    return False


def delete_key(key_id: str) -> bool:
    keys = persistence.load_api_keys()
    remaining = [k for k in keys if str(k["id"]) != str(key_id)]
    if len(remaining) == len(keys):
        return False
    persistence.save_api_keys(remaining)
    return True
