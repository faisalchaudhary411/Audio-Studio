"""
usage_tracking.py — the REAL enforcement backend for free-tier limits.

HISTORY: this module originally tracked IP-based usage but was never
actually wired into limit enforcement — app.py enforced everything purely
through the Flask session cookie, meaning any free user could reset every
limit by opening a private/incognito window, clearing cookies, or just
using a different browser, no network change even required. This version
replaces that: it's now the actual source of truth app.py's helper
functions (_under_limit, _bump_counter, etc.) delegate to.

APPROACH: each counter is tracked under TWO independent keys — one derived
from the connecting IP, one from a browser fingerprint (User-Agent +
Accept-Language + Sec-CH-UA). On every check, we resolve the EFFECTIVE
value as the MAX seen across both keys, then on every write we sync the
new value back to both. Concretely:
  - Switch browser, same network -> IP-keyed record still shows full
    history -> still enforced.
  - Switch network, same browser -> fingerprint-keyed record still shows
    full history -> still enforced.
  - Only switching BOTH simultaneously resets to zero — a meaningfully
    higher bar than either alone, without requiring an account/login system
    (which would be the only way to close this completely).

Every counter — daily action counts per tool, monthly character quota, and
anything else previously kept in the session — now lives in one merged
record per signal, containing both the day's counters and the month's char
total, so a single write always carries the complete current state.
"""

import hashlib
import datetime as dt
import threading

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
    identifying headers are present at all."""
    components = []
    ua = request.headers.get("User-Agent", "")
    if ua:
        components.append(ua)
    al = request.headers.get("Accept-Language", "")
    if al:
        components.append(al)
    ch = request.headers.get("Sec-CH-UA", "")
    if ch:
        components.append(ch)
    if components:
        return hashlib.sha256("|".join(components).encode()).hexdigest()[:16]
    return hash_ip(get_client_ip(request))


def _today() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def _this_month() -> str:
    return dt.datetime.now().strftime("%Y-%m")


# In-process cache so we don't hit the DB on every single request; writes
# flush to SQLite in a background thread. Fine for a single-VPS deployment;
# if this ever runs as multiple separate instances, this cache won't be
# shared between them.
_usage_cache = None
_usage_cache_lock = threading.Lock()


def _load_cache() -> dict:
    global _usage_cache
    if _usage_cache is None:
        with _usage_cache_lock:
            if _usage_cache is None:
                _usage_cache = persistence.load_usage()
    return _usage_cache


def _keys_for(request) -> tuple:
    ip_key = "ip:" + hash_ip(get_client_ip(request))
    fp_key = "fp:" + get_browser_fingerprint(request)
    return ip_key, fp_key


def _fresh_record() -> dict:
    return {"day": _today(), "daily": {}, "month": _this_month(), "chars_monthly": 0}


def _effective_record(request) -> dict:
    """Resolves the MAX across the IP-keyed and fingerprint-keyed records,
    for the CURRENT day/month only — a record from a previous day/month
    doesn't count toward today's totals, same as the old reset-if-needed
    behavior, just computed on read instead of via a separate reset step."""
    today = _today()
    month = _this_month()
    ip_key, fp_key = _keys_for(request)
    data = _load_cache()
    result = _fresh_record()
    for key in (ip_key, fp_key):
        rec = data.get(key, {})
        if rec.get("day") == today:
            for k, v in rec.get("daily", {}).items():
                if v > result["daily"].get(k, 0):
                    result["daily"][k] = v
        if rec.get("month") == month:
            if rec.get("chars_monthly", 0) > result["chars_monthly"]:
                result["chars_monthly"] = rec.get("chars_monthly", 0)
    return result


def _write_record(request, rec: dict):
    ip_key, fp_key = _keys_for(request)
    data = _load_cache()
    data[ip_key] = rec
    data[fp_key] = rec

    # Prune anything older than last month to keep the table small — a
    # record only needs to survive long enough for its own day/month
    # comparison to still matter.
    last_month = (dt.datetime.now().replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    data = {k: v for k, v in data.items() if v.get("month", "") >= last_month}

    global _usage_cache
    with _usage_cache_lock:
        _usage_cache = data

    def _bg_save(d):
        persistence.save_usage(d)
    threading.Thread(target=_bg_save, args=(data,), daemon=True).start()


# ---- public API used by app.py's _under_limit / _bump_counter / etc. ----

def get_daily_counter(request, counter_key: str) -> int:
    return _effective_record(request)["daily"].get(counter_key, 0)


def bump_daily_counter(request, counter_key: str):
    rec = _effective_record(request)
    rec["daily"][counter_key] = rec["daily"].get(counter_key, 0) + 1
    _write_record(request, rec)


def get_monthly_chars(request) -> int:
    return _effective_record(request)["chars_monthly"]


def bump_monthly_chars(request, chars_added: int):
    rec = _effective_record(request)
    rec["chars_monthly"] = rec.get("chars_monthly", 0) + chars_added
    _write_record(request, rec)
