"""
licensing.py — ported from your license-key system (generate_license_key,
create_new_key, revoke/unrevoke/delete_key, activate_vox_license,
check_vox_license, _is_subscription_active, _create_subscription_key) plus
verify_freemius_license.

Paddle is intentionally NOT ported — per your own history, Freemius replaced
Paddle after Paddle rejected the app, so Paddle is dead code in the original
too. If that's wrong and you still need Paddle, say so and I'll port it.

Device/IP matching uses Flask's request object instead of Streamlit's
websocket headers — see usage_tracking.py for the shared IP/fingerprint logic.
"""

import os
import random
import string
import datetime as dt
import requests

import persistence
from usage_tracking import get_client_ip, hash_ip, get_browser_fingerprint

FREEMIUS_API_TOKEN = os.environ.get("FREEMIUS_API_TOKEN", "").strip()
FREEMIUS_PRODUCT_ID = os.environ.get("FREEMIUS_PRODUCT_ID", "").strip()
FREEMIUS_SECRET_KEY = os.environ.get("FREEMIUS_SECRET_KEY", "").strip()


def _keys() -> dict:
    return persistence.load_license_keys()


def _save(keys: dict):
    persistence.save_license_keys(keys)


def generate_license_key() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=14))
    return f"VOXCRAFT-PRO-{suffix}"


def is_subscription_active(key_info: dict) -> bool:
    if not key_info:
        return False
    if key_info.get("revoked"):
        return False
    expires_at = key_info.get("expires_at")
    if expires_at:
        try:
            expiry = dt.datetime.strptime(expires_at, "%Y-%m-%d %H:%M")
            if dt.datetime.now() > expiry:
                return False
        except (ValueError, TypeError):
            pass
    return True


def sweep_expired_keys() -> int:
    """Explicitly marks any key past its expires_at as revoked=True.

    Access was already correctly being cut off without this — is_subscription_active()
    checks the expiry live on every call, so an expired key stops working
    immediately regardless of this sweep. This function exists purely so the
    admin panel's 'revoked' column is honest: without it, an expired
    grace-period or subscription key sits there looking identical to a
    genuinely active one until someone happens to look closely at
    expires_at. Safe to call as often as you like — already-revoked keys
    are simply skipped, and it never touches keys that are still within
    their valid window.

    Called from the admin dashboard and keys page on every load, so the
    picture is always current when you're actually looking at it — no
    separate scheduled job needed for a page nobody's looking at anyway.
    """
    keys = _keys()
    changed = 0
    now = dt.datetime.now()
    for key, info in keys.items():
        if info.get("revoked"):
            continue
        expires_at = info.get("expires_at")
        if not expires_at:
            continue
        try:
            expiry = dt.datetime.strptime(expires_at, "%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            continue
        if now > expiry:
            keys[key]["revoked"] = True
            changed += 1
    if changed:
        _save(keys)
    return changed


def create_subscription_key(customer_name: str, customer_email: str,
                             subscription_type: str = "monthly",
                             amount_paid: float = 0,
                             freemius_license_id: str = "",
                             expires_in_hours: float = None) -> str:
    key = generate_license_key()
    if expires_in_hours is not None:
        expires_at = (dt.datetime.now() + dt.timedelta(hours=expires_in_hours)).strftime("%Y-%m-%d %H:%M")
    elif subscription_type in ("monthly", "recurring"):
        expires_at = (dt.datetime.now() + dt.timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    else:
        expires_at = ""
    keys = _keys()
    keys[key] = {
        "used": False, "revoked": False,
        "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "activated_by": "", "activated_on": "",
        "customer_name": customer_name, "customer_email": customer_email,
        "subscription_type": subscription_type, "expires_at": expires_at,
        "freemius_license_id": freemius_license_id, "amount_paid": amount_paid,
        "renewal_count": 0, "activated_fp": "",
    }
    _save(keys)
    return key


def create_new_key_manual() -> str:
    """Admin-panel 'create a key by hand' button (e.g. for manual bank-transfer approvals)."""
    key = generate_license_key()
    keys = _keys()
    keys[key] = {
        "used": False, "revoked": False,
        "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "activated_by": "", "activated_on": "",
        "customer_name": "Manual", "customer_email": "",
        "subscription_type": "monthly",
        "expires_at": (dt.datetime.now() + dt.timedelta(days=30)).strftime("%Y-%m-%d %H:%M"),
        "amount_paid": 0, "renewal_count": 0, "activated_fp": "",
    }
    _save(keys)
    return key


def revoke_key(key: str):
    keys = _keys()
    if key in keys:
        keys[key]["revoked"] = True
        _save(keys)


def unrevoke_key(key: str):
    keys = _keys()
    if key in keys:
        keys[key]["revoked"] = False
        _save(keys)


def delete_key(key: str):
    keys = _keys()
    if key in keys:
        del keys[key]
        _save(keys)


def renew_subscription(key: str) -> bool:
    keys = _keys()
    if key not in keys:
        return False
    keys[key]["expires_at"] = (dt.datetime.now() + dt.timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    keys[key]["renewal_count"] = keys[key].get("renewal_count", 0) + 1
    _save(keys)
    return True


def _push_history(existing: list, value: str, cap: int = 5) -> list:
    """Append value to a rolling history list, most-recent-last, deduped,
    capped at `cap` entries (oldest dropped first). Used for both IP hashes
    and browser fingerprints so a key remembers the last few devices/browsers
    it was used from instead of only the single most recent one."""
    history = list(existing or [])
    if value and value in history:
        history.remove(value)
    if value:
        history.append(value)
    return history[-cap:]


def _is_same_device(info: dict, request) -> bool:
    """'Same device' = matches ANY recently-seen IP hash or fingerprint for
    this key, not just the single latest one. A key is meant to be locked to
    one physical device but usable from any browser on it — since IP is a
    network-level signal (not browser-specific), matching against a short
    rolling history covers the common case of switching browsers on the same
    wifi, or switching networks on the same browser, without requiring both
    to line up in the same instant the way a single "last seen" value did."""
    current_ip = get_client_ip(request)
    ip_history = info.get("activated_ips") or ([info["activated_by"]] if info.get("activated_by") else [])
    if current_ip != "unknown" and hash_ip(current_ip) in ip_history:
        return True
    current_fp = get_browser_fingerprint(request)
    fp_history = info.get("activated_fps") or ([info["activated_fp"]] if info.get("activated_fp") else [])
    return bool(current_fp) and current_fp in fp_history


def activate_vox_license(key: str, request) -> dict:
    """Activate/re-activate a key. Same-device re-activation is allowed even
    if IP changed (mirrors your original fix for mobile network switching).

    Uses persistence.license_key_transaction() instead of the old
    load-whole-dict/mutate/save-whole-dict pattern — that had a real race
    condition where two people activating the same not-yet-used key at
    nearly the same instant could both read "unused" before either write
    landed, and both succeed. The transaction closes that window: a second
    concurrent call for the same key blocks until the first fully commits.
    """
    key = key.strip()
    with persistence.license_key_transaction(key) as holder:
        info = holder["info"]
        if info is None:
            return {"valid": False, "error": "Invalid license key."}

        if not is_subscription_active(info):
            return {"valid": False, "error": "Your subscription has expired. Please renew your plan."}
        if info.get("revoked"):
            return {"valid": False, "error": "This key has been revoked. Contact support."}

        if info.get("used"):
            if _is_same_device(info, request):
                current_ip = get_client_ip(request)
                if current_ip != "unknown":
                    ip_hash = hash_ip(current_ip)
                    info["activated_ips"] = _push_history(info.get("activated_ips"), ip_hash)
                    info["activated_by"] = ip_hash  # kept for backward compat / admin display
                current_fp = get_browser_fingerprint(request)
                info["activated_fps"] = _push_history(info.get("activated_fps"), current_fp)
                info["activated_fp"] = current_fp  # kept for backward compat / admin display
                info["activated_on"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
                holder["info"] = info
                return {"valid": True, "name": info.get("customer_name", "Pro User")}
            return {"valid": False, "error": "This key has already been used on another device."}

        info["used"] = True
        info["activated_on"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        current_ip = get_client_ip(request)
        if current_ip != "unknown":
            ip_hash = hash_ip(current_ip)
            info["activated_by"] = ip_hash
            info["activated_ips"] = [ip_hash]
        current_fp = get_browser_fingerprint(request)
        info["activated_fp"] = current_fp
        info["activated_fps"] = [current_fp]
        holder["info"] = info
        return {"valid": True, "name": info.get("customer_name", "Pro User")}


def find_key_by_freemius_id(freemius_license_id: str) -> str:
    """Avoids minting a fresh internal key every time the same Freemius
    license is entered — reuse the one already created for it, if any."""
    if not freemius_license_id:
        return ""
    for key, info in _keys().items():
        if info.get("freemius_license_id") == freemius_license_id:
            return key
    return ""


def activate_via_freemius(freemius_key: str, request) -> dict:
    """Verify a key against Freemius, then wrap it in one of our own internal
    keys so it flows through the same activate/check/device-binding/admin
    visibility as every other key. Called only when the key isn't found in
    our own license_keys.json (see activate_any_license below)."""
    result = verify_freemius_license(freemius_key)
    if not result.get("success"):
        return {"valid": False, "error": result.get("error") or "Could not reach Freemius to verify this key."}
    if not result.get("valid"):
        return {"valid": False, "error": result.get("error") or "This Freemius license isn't active."}

    fs_id = result.get("freemius_license_id", "")
    internal_key = find_key_by_freemius_id(fs_id)
    if not internal_key:
        internal_key = create_subscription_key(
            result.get("customer_name", "Pro User"),
            result.get("customer_email", ""),
            subscription_type="recurring",
            freemius_license_id=fs_id,
        )

    activation = activate_vox_license(internal_key, request)
    if not activation.get("valid"):
        return activation
    return {"valid": True, "name": activation.get("name"), "internal_key": internal_key}


def activate_any_license(key: str, request) -> dict:
    """Single entry point for the /activate page: tries our own internal keys
    first (no network call), and only falls back to Freemius verification if
    the key isn't one of ours — avoids an unnecessary Freemius API call for
    the common case (manual bank-transfer customers)."""
    key = key.strip()
    if key in _keys():
        return activate_vox_license(key, request)
    return activate_via_freemius(key, request)


def check_vox_license(key: str) -> dict:
    """Read-only check — used to keep a session's Pro status accurate without
    re-triggering activation/device-binding logic on every request."""
    key = key.strip()
    info = _keys().get(key)
    if not info:
        return {"valid": False}
    if not is_subscription_active(info):
        return {"valid": False, "error": "Subscription expired"}
    if info.get("revoked"):
        return {"valid": False}
    return {"valid": True, "name": info.get("customer_name", "Pro User")}


def verify_freemius_license(license_key: str) -> dict:
    """Verify against Freemius, then mint one of our own internal keys so it
    flows through the same activate/check functions as manual + any other flow."""
    if not FREEMIUS_API_TOKEN or not FREEMIUS_PRODUCT_ID:
        return {"success": False, "valid": False, "error": "Freemius not configured on this deployment."}
    if not license_key:
        return {"success": False, "valid": False, "error": "No license key provided."}
    try:
        r = requests.get(
            f"https://api.freemius.com/v1/products/{FREEMIUS_PRODUCT_ID}/licenses/{license_key}.json",
            headers={"Authorization": f"Bearer {FREEMIUS_API_TOKEN}"},
            timeout=15,
        )
        if r.status_code != 200:
            return {"success": False, "valid": False, "error": f"HTTP {r.status_code}"}
        data = r.json()
        is_cancelled = bool(data.get("is_cancelled", False))
        expiration = data.get("expiration")
        is_expired = False
        if expiration:
            try:
                is_expired = dt.datetime.strptime(expiration, "%Y-%m-%d %H:%M:%S") < dt.datetime.now()
            except Exception:
                is_expired = False
        is_valid = (not is_cancelled) and (not is_expired)
        return {
            "success": True, "valid": is_valid,
            "freemius_license_id": data.get("id", ""),
            "customer_email": data.get("user_email", "") or data.get("email", ""),
            "customer_name": data.get("user_name", "") or "Pro User",
            "expires_at": expiration or "",
            "error": None if is_valid else ("License cancelled" if is_cancelled else "License expired"),
        }
    except Exception as e:
        return {"success": False, "valid": False, "error": str(e)}


def _normalize_freemius_date(raw: str) -> str:
    """Freemius's API/webhooks return dates like '2026-09-04 12:00:00'
    (with seconds); our internal storage format is '%Y-%m-%d %H:%M' (no
    seconds, matching create_subscription_key/is_subscription_active).
    Falls back to a blind +30-days-from-now if the date can't be parsed at
    all, so a malformed/unexpected payload never leaves the key stuck with
    no expiry — worse case is one cycle needs a manual look, not silent
    infinite access."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(raw, fmt).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            continue
    return (dt.datetime.now() + dt.timedelta(days=30)).strftime("%Y-%m-%d %H:%M")


def sync_license_from_freemius_event(freemius_license_id: str, event_type: str, new_expiration: str = "") -> dict:
    """Called from the /webhook/freemius route on license.extended /
    license.cancelled / license.expired events — keeps our internal key's
    expiry in sync with what Freemius actually billed, rather than blindly
    assuming every renewal is exactly +30 days (wrong for annual plans, and
    wrong if Freemius ever prorates/adjusts a period).

    This is the piece that was missing entirely before: nothing previously
    extended a key's expiry when a recurring subscription renewed, so every
    Pro customer — even ones still being billed monthly — would lose access
    at the 30-day mark regardless of continued payment.
    """
    if not freemius_license_id:
        return {"success": False, "error": "No freemius_license_id in webhook payload."}

    key = find_key_by_freemius_id(freemius_license_id)
    if not key:
        return {"success": False, "error": f"No internal key found for Freemius license {freemius_license_id} — was it ever activated via fs_callback?"}

    keys = _keys()
    info = keys[key]

    if event_type == "license.extended":
        info["expires_at"] = _normalize_freemius_date(new_expiration) if new_expiration else \
            (dt.datetime.now() + dt.timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
        info["revoked"] = False  # a successful renewal recovers from any prior dunning-related revoke
        info["renewal_count"] = info.get("renewal_count", 0) + 1
        _save(keys)
        return {"success": True, "action": "extended", "key": key, "new_expiry": info["expires_at"]}

    if event_type == "license.expired":
        # Safety-net revoke — if our expires_at was already in sync via
        # license.extended events this is usually redundant, but covers the
        # case where a renewal silently failed to sync for any reason.
        info["revoked"] = True
        _save(keys)
        return {"success": True, "action": "revoked_expired", "key": key}

    if event_type == "license.cancelled":
        # Deliberately NOT revoking here — Freemius keeps the license valid
        # through the end of the period the customer already paid for, and
        # simply won't fire another license.extended after this. Just
        # tagging it for admin visibility so cancellations are visible in
        # the admin keys list without cutting the customer off early.
        info["subscription_type"] = "cancelled"
        _save(keys)
        return {"success": True, "action": "tagged_cancelled", "key": key}

    return {"success": False, "error": f"Unhandled event type: {event_type}"}
