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


def create_subscription_key(customer_name: str, customer_email: str,
                             subscription_type: str = "monthly",
                             amount_paid: float = 0,
                             freemius_license_id: str = "") -> str:
    key = generate_license_key()
    expires_at = (dt.datetime.now() + dt.timedelta(days=30)).strftime("%Y-%m-%d %H:%M") \
        if subscription_type in ("monthly", "recurring") else ""
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


def _is_same_device(info: dict, request) -> bool:
    current_ip = get_client_ip(request)
    if current_ip != "unknown" and info.get("activated_by") == hash_ip(current_ip):
        return True
    current_fp = get_browser_fingerprint(request)
    stored_fp = info.get("activated_fp", "")
    return bool(stored_fp) and current_fp == stored_fp


def activate_vox_license(key: str, request) -> dict:
    """Activate/re-activate a key. Same-device re-activation is allowed even
    if IP changed (mirrors your original fix for mobile network switching)."""
    key = key.strip()
    keys = _keys()
    if key not in keys:
        return {"valid": False, "error": "Invalid license key."}

    info = keys[key]
    if not is_subscription_active(info):
        return {"valid": False, "error": "Your subscription has expired. Please renew your plan."}
    if info.get("revoked"):
        return {"valid": False, "error": "This key has been revoked. Contact support."}

    if info.get("used"):
        if _is_same_device(info, request):
            current_ip = get_client_ip(request)
            if current_ip != "unknown":
                keys[key]["activated_by"] = hash_ip(current_ip)
            keys[key]["activated_fp"] = get_browser_fingerprint(request)
            keys[key]["activated_on"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            _save(keys)
            return {"valid": True, "name": info.get("customer_name", "Pro User")}
        return {"valid": False, "error": "This key has already been used on another device."}

    keys[key]["used"] = True
    keys[key]["activated_on"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    current_ip = get_client_ip(request)
    if current_ip != "unknown":
        keys[key]["activated_by"] = hash_ip(current_ip)
    keys[key]["activated_fp"] = get_browser_fingerprint(request)
    _save(keys)
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
