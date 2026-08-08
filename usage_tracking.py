"""
usage_tracking.py — ported from _get_user_ip / _hash_ip / _get_browser_fingerprint
/ _is_same_device / get_ip_usage / update_ip_usage / ip_check_limit.

This is the piece that was previously a session-cookie stub in app.py's
is_pro()/_check_and_bump — now it's real IP-based tracking, persisted via
persistence.py (SQLite on the VPS) rather than per-browser state.
"""

import os
import hashlib
import datetime as dt
import threading

import persistence


def get_client_ip(request) -> str:
    """HARDENING (VPS deploy): the old version trusted the *first* entry in
    X-Forwarded-For. That's exactly the part a client fully controls — anyone
    could send their own fake X-Forwarded-For header and get a fresh "IP" on
    every request, bypassing IP-based usage limits and license binding
    entirely. With ProxyFix + a correctly configured Nginx (see deploy
    notes), request.remote_addr is now Nginx's trusted resolution of the
    real client IP — the one signal a client cannot spoof — so that's the
    primary source. X-Real-IP (set once by Nginx, never client-supplied) is
    kept as a fallback for setups where ProxyFix isn't in the request path.
    """
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip.strip()
    return request.remote_addr or "unknown"


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def get_browser_fingerprint(request) -> str:
    """Stable fingerprint from headers, falling back to IP hash.
    Lets a key re-activate on the same device even if the network/IP changes
    (e.g. mobile data <-> wifi), same rationale as your original."""
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


# In-process cache so we don't hit GitHub on every single request; a background
# thread flushes to GitHub. Fine for a single Render instance; if you ever run
# multiple instances this cache won't be shared between them (same caveat as
# clone_engine's job store).
_usage_cache = None
_usage_cache_lock = threading.Lock()


def _load_cache() -> dict:
    global _usage_cache
    if _usage_cache is None:
        with _usage_cache_lock:
            if _usage_cache is None:
                _usage_cache = persistence.load_usage()
    return _usage_cache


def get_ip_usage(request) -> dict:
    month = dt.datetime.now().strftime("%Y-%m")
    ip_hash = hash_ip(get_client_ip(request))
    data = _load_cache()
    record = data.get(ip_hash, {})
    if record.get("month") != month:
        return {"month": month, "chars_used": 0, "generations": 0}
    return record


def update_ip_usage(request, chars_added: int = 0, generations_added: int = 0):
    month = dt.datetime.now().strftime("%Y-%m")
    ip_hash = hash_ip(get_client_ip(request))
    data = _load_cache()
    record = data.get(ip_hash, {"month": month, "chars_used": 0, "generations": 0})
    if record.get("month") != month:
        record = {"month": month, "chars_used": 0, "generations": 0}
    record["chars_used"] = record.get("chars_used", 0) + chars_added
    record["generations"] = record.get("generations", 0) + generations_added
    record["month"] = month
    data[ip_hash] = record

    # prune entries older than last month to keep the file small
    last_month = (dt.datetime.now().replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    data = {k: v for k, v in data.items() if v.get("month", "") >= last_month}

    global _usage_cache
    with _usage_cache_lock:
        _usage_cache = data

    def _bg_save(d):
        persistence.save_usage(d)
    threading.Thread(target=_bg_save, args=(data,), daemon=True).start()


def ip_chars_used(request) -> int:
    return get_ip_usage(request).get("chars_used", 0)


def ip_check_limit(request, text_len: int, char_limit: int, is_pro: bool) -> bool:
    """Returns True if adding text_len chars would EXCEED the free monthly limit."""
    if is_pro:
        return False
    return ip_chars_used(request) + text_len > char_limit
