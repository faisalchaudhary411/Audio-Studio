"""
usage_tracking.py — ported from _get_user_ip / _hash_ip / _get_browser_fingerprint
/ _is_same_device / get_ip_usage / update_ip_usage / ip_check_limit.

This is the piece that was previously a session-cookie stub in app.py's
is_pro()/_check_and_bump — now it's real IP-based tracking synced to GitHub,
matching your original Streamlit app's actual behavior (not per-browser).

Note on Render specifically: Render sits behind a proxy, so request.remote_addr
alone gives the proxy's IP, not the visitor's. X-Forwarded-For is what you want,
same as the original code's header-checking logic.
"""

import os
import hashlib
import datetime as dt
import threading

import persistence

GH_REPO = persistence.GH_REPO  # noqa: for clarity when reading this file


def get_client_ip(request) -> str:
    for header in ("X-Forwarded-For", "X-Real-IP"):
        val = request.headers.get(header, "")
        if val:
            return val.split(",")[0].strip()
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
