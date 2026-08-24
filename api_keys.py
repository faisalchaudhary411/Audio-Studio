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
"""
import hashlib
import secrets
import datetime as dt

import persistence

KEY_PREFIX = "vox_live_"


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


def create_api_key(customer_name: str, customer_email: str, plan: str, monthly_char_quota: int,
                    freemius_license_id: str = None) -> dict:
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
    }
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


def get_usage(key_hash: str) -> dict:
    """Read-only usage snapshot for the CURRENT period — resets the
    displayed character count to 0 once the period rolls over, without
    needing a separate cleanup job (old months' data just sits unused in
    the table; negligible size at this scale). last_used is preserved
    across the period boundary regardless — "when was this key last
    used" shouldn't reset just because the calendar flipped to a new
    month."""
    usage = persistence.peek_api_key_usage(key_hash)
    period = _current_period()
    if usage.get("period") != period:
        return {"period": period, "chars_used": 0, "last_used": usage.get("last_used")}
    return usage


def would_exceed_quota(record: dict, char_count: int) -> bool:
    """Read-only check — call BEFORE doing the actual generation work, so
    a request that's going to be rejected never touches the TTS engine."""
    usage = get_usage(record["key_hash"])
    return usage["chars_used"] + char_count > record["monthly_char_quota"]


def bump_usage(key_hash: str, char_count: int):
    """Only call AFTER a generation actually succeeds — mirrors
    app.py's _bump_monthly_chars() pattern for the browser-based free
    tier, for the same reason (a failed generation, e.g. a TTS engine
    error, should never consume quota the customer is paying for).

    Also stamps last_used here, in the SAME atomic transaction, rather
    than as a separate write to the api_keys metadata table — writing
    "last used" on every single API call would reintroduce exactly the
    concurrent-write risk this module went out of its way to avoid for
    the character counter, just for a timestamp instead of a number."""
    period = _current_period()
    with persistence.api_key_usage_transaction(key_hash) as holder:
        usage = holder["usage"]
        if not usage or usage.get("period") != period:
            usage = {"period": period, "chars_used": 0}
        usage["chars_used"] += char_count
        usage["last_used"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        holder["usage"] = usage


def revoke_key(key_id: str) -> bool:
    keys = persistence.load_api_keys()
    for k in keys:
        if str(k["id"]) == str(key_id):
            k["active"] = False
            persistence.save_api_keys(keys)
            return True
    return False


def unrevoke_key(key_id: str) -> bool:
    keys = persistence.load_api_keys()
    for k in keys:
        if str(k["id"]) == str(key_id):
            k["active"] = True
            persistence.save_api_keys(keys)
            return True
    return False


def delete_key(key_id: str) -> bool:
    keys = persistence.load_api_keys()
    remaining = [k for k in keys if str(k["id"]) != str(key_id)]
    if len(remaining) == len(keys):
        return False
    persistence.save_api_keys(remaining)
    return True
