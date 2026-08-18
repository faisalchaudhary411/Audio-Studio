"""
usage_tracking.py — the REAL enforcement backend for free-tier limits.

HISTORY, PART 1: this module originally tracked IP-based usage but was
never actually wired into limit enforcement — app.py enforced everything
purely through the Flask session cookie, meaning any free user could reset
every limit by opening a private/incognito window, clearing cookies, or
just using a different browser, no network change even required. An
earlier version of this module replaced that with dual-keyed tracking (see
the IP+fingerprint explanation below) — but backed by ONE in-process dict,
loaded once per gunicorn worker and periodically flushed to SQLite with a
full-table DELETE+reinsert.

HISTORY, PART 2 — the cross-worker bug: deploy/voxcraft.service runs
`--workers 2`, which is two separate OS processes, not threads. Python
globals (including that in-process dict) aren't shared across a fork after
--preload hands off to the workers. In practice that meant:
  - Under-enforcement: a free visitor's requests land on worker A and
    worker B roughly alternately under normal load. Each worker only
    enforced against the increments IT had personally processed, since it
    never re-read the other worker's writes from disk after its own first
    load — so a visitor could get up to ~2x the configured daily limit
    just from ordinary request routing, no cookie-clearing required.
  - Data loss: the periodic full-table flush from one worker's stale
    in-memory snapshot could silently overwrite counts a DIFFERENT worker
    had just written for a DIFFERENT visitor, since "save everything I
    currently have in memory" has no way to know what the sibling process
    wrote in the meantime.

FIXED by removing the in-process cache entirely. Every check and every
bump now goes through persistence.usage_pair_transaction(), which does the
read-modify-write inside one real SQLite transaction (BEGIN IMMEDIATE) —
the same pattern already used for license key activation
(persistence.license_key_transaction()). Correctness now comes from
SQLite's own cross-process file locking, not from anything held in this
process's memory, so it's correct regardless of which worker handles which
request, and there's no more periodic whole-table rewrite to clobber
anything. This does mean one small SQLite transaction per check/bump
instead of an in-memory lookup — on a local WAL-mode SQLite file this is
sub-millisecond and not a meaningful cost at this project's traffic level.

APPROACH (unchanged from before): each counter is tracked under TWO
independent keys — one derived from the connecting IP, one from a browser
fingerprint (User-Agent + Accept-Language + Sec-CH-UA). On every check, we
resolve the EFFECTIVE value as the MAX seen across both keys, then on
every write we sync the new value back to both. Concretely:
  - Switch browser, same network -> IP-keyed record still shows full
    history -> still enforced.
  - Switch network, same browser -> fingerprint-keyed record still shows
    full history -> still enforced.
  - Only switching BOTH simultaneously resets to zero — a meaningfully
    higher bar than either alone, without requiring an account/login system
    (which would be the only way to close this completely).

Every counter — daily action counts per tool, monthly character quota, and
anything else previously kept in the session — lives in one merged record
per signal, containing both the day's counters and the month's char total,
so a single write always carries the complete current state for that key.
"""

import hashlib
import re
import datetime as dt

import persistence


def get_client_ip(request) -> str:
    """Prefers X-Real-IP (set once by Nginx, never client-supplied) — the
    one signal a client cannot spoof. Falls back to remote_addr, which
    ProxyFix correctly resolves from a trusted X-Forwarded-For hop when
    X-Real-IP isn't present."""
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip.strip()
    return request.remote_addr or "unknown"


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def get_browser_fingerprint(request) -> str:
    """Stable fingerprint from headers, falling back to IP hash if no
    identifying headers are present at all.

    BUG FIX: version numbers are stripped from every component before
    hashing. The original version hashed the raw User-Agent (and Sec-CH-UA,
    which also embeds a version) as-is — but Chrome auto-updates every few
    weeks, which changes the version number embedded in both headers,
    which silently changed the fingerprint for every returning visitor.
    For licensing.py's device-lock (which requires this fingerprint to
    match stored history to reactivate or silently auto-restore Pro), that
    meant a routine browser update could lock a paying customer out of
    their own key with no warning and no obvious cause — confirmed in
    production (voxcraft.site, Aug 2026): a customer's reactivation was
    rejected with "already used on another device" despite it being the
    same phone and same Chrome install, because the Chrome version ticked
    over between visits. Stripping digits keeps the parts of the
    fingerprint that actually distinguish devices (OS, device model,
    language, mobile vs desktop) while dropping the part that changes
    under the visitor without them doing anything."""
    components = []
    ua = request.headers.get("User-Agent", "")
    if ua:
        components.append(re.sub(r"\d[\d.]*", "", ua))
    al = request.headers.get("Accept-Language", "")
    if al:
        # Only the primary language tag, and only the tag itself — the full
        # header can include a weighted list (e.g. "en-US,en;q=0.9") whose
        # order/weights some browsers vary between requests on the same
        # device, and the ";q=" weight is itself a number that could drift.
        components.append(al.split(",")[0].split(";")[0].strip())
    ch = request.headers.get("Sec-CH-UA", "")
    if ch:
        components.append(re.sub(r"\d[\d.]*", "", ch))
    if components:
        return hashlib.sha256("|".join(components).encode()).hexdigest()[:16]
    return hash_ip(get_client_ip(request))


def _today() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def _this_month() -> str:
    return dt.datetime.now().strftime("%Y-%m")


def _keys_for(request) -> tuple:
    ip_key = "ip:" + hash_ip(get_client_ip(request))
    fp_key = "fp:" + get_browser_fingerprint(request)
    return ip_key, fp_key


def _fresh_record() -> dict:
    return {"day": _today(), "daily": {}, "month": _this_month(), "chars_monthly": 0}


def _merge(rec_a, rec_b) -> dict:
    """Resolves the MAX across the two records, for the CURRENT day/month
    only — a record from a previous day/month doesn't count toward today's
    totals."""
    today = _today()
    month = _this_month()
    result = _fresh_record()
    for rec in (rec_a, rec_b):
        if not rec:
            continue
        if rec.get("day") == today:
            for k, v in rec.get("daily", {}).items():
                if v > result["daily"].get(k, 0):
                    result["daily"][k] = v
        if rec.get("month") == month:
            if rec.get("chars_monthly", 0) > result["chars_monthly"]:
                result["chars_monthly"] = rec.get("chars_monthly", 0)
    return result


# ---- public API used by app.py's _under_limit / _bump_counter / etc. ----

def get_daily_counter(request, counter_key: str) -> int:
    ip_key, fp_key = _keys_for(request)
    with persistence.usage_pair_transaction(ip_key, fp_key) as holder:
        merged = _merge(holder["a"], holder["b"])
        # read-only: leave holder["record"] as None so nothing gets written
    return merged["daily"].get(counter_key, 0)


def bump_daily_counter(request, counter_key: str):
    ip_key, fp_key = _keys_for(request)
    with persistence.usage_pair_transaction(ip_key, fp_key) as holder:
        merged = _merge(holder["a"], holder["b"])
        merged["daily"][counter_key] = merged["daily"].get(counter_key, 0) + 1
        holder["record"] = merged


def get_monthly_chars(request) -> int:
    ip_key, fp_key = _keys_for(request)
    with persistence.usage_pair_transaction(ip_key, fp_key) as holder:
        merged = _merge(holder["a"], holder["b"])
    return merged["chars_monthly"]


def bump_monthly_chars(request, chars_added: int):
    ip_key, fp_key = _keys_for(request)
    with persistence.usage_pair_transaction(ip_key, fp_key) as holder:
        merged = _merge(holder["a"], holder["b"])
        merged["chars_monthly"] = merged.get("chars_monthly", 0) + chars_added
        holder["record"] = merged
