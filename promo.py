"""
promo.py — one-time promo codes for free plan grants and percentage discounts.

Two code types:

1. type="free"
   Admin sets: code, expires_at, plan (pro|pro_plus|api_starter|api_pro|all),
   duration_months (1|2|3).
   Redeem once → issues a real license key (or API key) for that plan lasting
   duration_months. New users get the set-password email; existing account
   users see the key immediately.

2. type="discount"
   Admin sets: code, expires_at, discount_percent (1-100).
   Redeem once on the upgrade / manual-payment path → price is reduced by
   that percent. Freemius card checkouts use the matching coupon the admin
   creates in the Freemius dashboard (same code string); this module only
   tracks the one-time use and applies the discount for the manual PKR path.

Hard one-time rules (tightened per product requirement):
- One redemption per normalised email, AND
- One redemption per browser fingerprint, AND
- One redemption per IP hash
  → even if the same person tries a second email from the same device /
    browser / network, the second attempt is rejected.
"""

from __future__ import annotations

import datetime as dt
import random
import re
import string
import uuid

import persistence
import licensing
import api_keys
import accounts
import notifications
from usage_tracking import get_client_ip, hash_ip, get_browser_fingerprint


# Individual selectable plans for free promos. Multiple may be combined
# on one code (e.g. pro + api_starter). "all" is a shortcut for every plan.
VALID_FREE_PLANS = ("pro", "pro_plus", "api_starter", "api_pro")
VALID_FREE_PLAN_SET = set(VALID_FREE_PLANS) | {"all"}
VALID_DURATIONS = (1, 2, 3)


def _normalize_plans(plan) -> list:
    """Accept a string, comma-separated string, or list; return sorted unique plan list."""
    if plan is None:
        return []
    if isinstance(plan, (list, tuple, set)):
        raw = list(plan)
    else:
        raw = re.split(r"[\s,]+", str(plan).strip().lower()) if str(plan).strip() else []
    out = []
    for p in raw:
        p = (p or "").strip().lower()
        if not p:
            continue
        if p == "all":
            return list(VALID_FREE_PLANS)
        if p in VALID_FREE_PLAN_SET and p not in out:
            out.append(p)
    return out


def _now_iso() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def normalize_code(raw: str) -> str:
    return (raw or "").strip().upper().replace(" ", "")


def generate_code(length: int = 10) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def create_promo(
    code: str = "",
    promo_type: str = "free",
    plan: str = "pro",
    duration_months: int = 1,
    discount_percent: int = 0,
    expires_at: str = "",
    max_uses: int = 0,
    note: str = "",
) -> tuple[bool, str, dict]:
    """
    Create a new promo code. Returns (ok, message, record).
    max_uses=0 means unlimited (still one-per-user).
    """
    code = normalize_code(code) or generate_code()
    if not code or len(code) < 4:
        return False, "Code must be at least 4 characters.", {}

    codes = persistence.load_promo_codes()
    if code in codes:
        return False, f"Code '{code}' already exists.", {}

    promo_type = (promo_type or "free").strip().lower()
    if promo_type not in ("free", "discount"):
        return False, "Type must be 'free' or 'discount'.", {}

    plans = []
    if promo_type == "free":
        plans = _normalize_plans(plan)
        if not plans:
            return False, "Select at least one plan (Pro, Pro+, API Starter, and/or API Pro).", {}
        bad = [p for p in plans if p not in VALID_FREE_PLANS]
        if bad:
            return False, f"Invalid plan(s): {bad}. Choose from {VALID_FREE_PLANS}.", {}
        try:
            duration_months = int(duration_months)
        except (TypeError, ValueError):
            return False, "Duration must be 1, 2 or 3 months.", {}
        if duration_months not in VALID_DURATIONS:
            return False, "Duration must be 1, 2 or 3 months.", {}
        discount_percent = 0
    else:
        plans = []
        duration_months = 0
        try:
            discount_percent = int(discount_percent)
        except (TypeError, ValueError):
            return False, "Discount percent must be an integer 1–100.", {}
        if not (1 <= discount_percent <= 100):
            return False, "Discount percent must be between 1 and 100.", {}

    expires_at = (expires_at or "").strip()
    if expires_at:
        try:
            dt.datetime.strptime(expires_at[:10], "%Y-%m-%d")
        except ValueError:
            return False, "Expiry date must be YYYY-MM-DD.", {}

    try:
        max_uses = int(max_uses or 0)
    except (TypeError, ValueError):
        max_uses = 0

    record = {
        "code": code,
        "type": promo_type,
        # plans = list for multi-select; plan = comma string for older UI/display
        "plans": plans,
        "plan": ",".join(plans) if plans else "",
        "duration_months": duration_months,
        "discount_percent": discount_percent,
        "expires_at": expires_at[:10] if expires_at else "",
        "max_uses": max_uses,
        "uses_count": 0,
        "active": True,
        "note": (note or "").strip()[:200],
        "created_at": _now_iso(),
    }
    codes[code] = record
    ok, err = persistence.save_promo_codes(codes)
    if not ok:
        return False, f"Save failed: {err}", {}
    return True, "Promo code created.", record


def deactivate_promo(code: str) -> tuple[bool, str]:
    code = normalize_code(code)
    codes = persistence.load_promo_codes()
    if code not in codes:
        return False, "Code not found."
    codes[code]["active"] = False
    ok, err = persistence.save_promo_codes(codes)
    return (ok, "Deactivated." if ok else err)


def activate_promo(code: str) -> tuple[bool, str]:
    code = normalize_code(code)
    codes = persistence.load_promo_codes()
    if code not in codes:
        return False, "Code not found."
    codes[code]["active"] = True
    ok, err = persistence.save_promo_codes(codes)
    return (ok, "Activated." if ok else err)


def delete_promo(code: str) -> tuple[bool, str]:
    code = normalize_code(code)
    codes = persistence.load_promo_codes()
    if code not in codes:
        return False, "Code not found."
    del codes[code]
    ok, err = persistence.save_promo_codes(codes)
    return (ok, "Deleted." if ok else err)


def list_promos() -> list:
    codes = persistence.load_promo_codes()
    rows = list(codes.values())
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


def _is_expired(record: dict) -> bool:
    exp = (record.get("expires_at") or "").strip()
    if not exp:
        return False
    try:
        return _today() > exp[:10]
    except Exception:
        return False


def _already_redeemed(code: str, email: str, ip_hash: str, fp: str) -> str | None:
    """
    Returns a human-readable reason if this user/device already redeemed
    ANY promo (or this specific code), else None.
    Policy: one redemption ever per email, per fingerprint, per IP.
    """
    email = (email or "").strip().lower()
    redemptions = persistence.load_promo_redemptions()
    for r in redemptions:
        if r.get("code") == code and email and r.get("email") == email:
            return "You have already used this promo code."
        if email and r.get("email") == email:
            return "This email has already redeemed a promo code."
        if fp and r.get("fingerprint") == fp:
            return "This device has already redeemed a promo code."
        if ip_hash and r.get("ip_hash") == ip_hash:
            return "A promo code has already been used from this network."
    return None


def validate_for_discount(code: str, email: str, request) -> tuple[bool, str, dict]:
    """
    Check a discount code without consuming it. Used by the upgrade page
    to show the reduced price before the user submits payment.
    Returns (ok, message, promo_record).
    """
    code = normalize_code(code)
    if not code:
        return False, "Enter a promo code.", {}

    codes = persistence.load_promo_codes()
    rec = codes.get(code)
    if not rec:
        return False, "Invalid promo code.", {}
    if not rec.get("active", True):
        return False, "This promo code is no longer active.", {}
    if _is_expired(rec):
        return False, "This promo code has expired.", {}
    if rec.get("type") != "discount":
        return False, "This code is a free-plan code. Use it on the Redeem page instead.", {}
    if rec.get("max_uses") and int(rec.get("uses_count", 0)) >= int(rec["max_uses"]):
        return False, "This promo code has reached its usage limit.", {}

    ip_hash = hash_ip(get_client_ip(request))
    fp = get_browser_fingerprint(request)
    blocked = _already_redeemed(code, email, ip_hash, fp)
    if blocked:
        return False, blocked, {}

    return True, f"{rec['discount_percent']}% discount applied.", rec


def consume_discount(code: str, email: str, request, plan: str = "", amount_before: float = 0) -> tuple[bool, str, dict]:
    """
    Mark a discount code as used after the user has submitted a payment
    request (or right before creating the manual request). Returns the
    promo record on success.
    """
    ok, msg, rec = validate_for_discount(code, email, request)
    if not ok:
        return False, msg, {}

    email = (email or "").strip().lower()
    ip_hash = hash_ip(get_client_ip(request))
    fp = get_browser_fingerprint(request)

    redemption = {
        "id": str(uuid.uuid4()),
        "code": code,
        "type": "discount",
        "email": email,
        "ip_hash": ip_hash,
        "fingerprint": fp,
        "plan": plan or "",
        "discount_percent": rec.get("discount_percent", 0),
        "amount_before": amount_before,
        "redeemed_at": _now_iso(),
    }
    redemptions = persistence.load_promo_redemptions()
    redemptions.insert(0, redemption)
    persistence.save_promo_redemptions(redemptions)

    codes = persistence.load_promo_codes()
    if code in codes:
        codes[code]["uses_count"] = int(codes[code].get("uses_count", 0)) + 1
        persistence.save_promo_codes(codes)

    return True, "Discount applied.", rec


def redeem_free(code: str, email: str, name: str, request, site_url: str = "") -> tuple[bool, str, dict]:
    """
    Redeem a free-plan promo. Creates the appropriate license or API key,
    provisions the account, and either emails the set-password link (new
    user) or returns the key for immediate display (existing user).

    Returns (ok, message, result_dict) where result_dict may contain:
      - key / raw_key
      - plan
      - is_new_account
      - expires_at
    """
    code = normalize_code(code)
    email = (email or "").strip().lower()
    name = (name or "").strip() or "Promo User"

    if not code:
        return False, "Enter a promo code.", {}
    if not email or "@" not in email:
        return False, "A valid email is required.", {}

    codes = persistence.load_promo_codes()
    rec = codes.get(code)
    if not rec:
        return False, "Invalid promo code.", {}
    if not rec.get("active", True):
        return False, "This promo code is no longer active.", {}
    if _is_expired(rec):
        return False, "This promo code has expired.", {}
    if rec.get("type") != "free":
        return False, "This is a discount code. Enter it on the Upgrade / payment page instead.", {}
    if rec.get("max_uses") and int(rec.get("uses_count", 0)) >= int(rec["max_uses"]):
        return False, "This promo code has reached its usage limit.", {}

    ip_hash = hash_ip(get_client_ip(request))
    fp = get_browser_fingerprint(request)
    blocked = _already_redeemed(code, email, ip_hash, fp)
    if blocked:
        return False, blocked, {}

    # Support multi-plan codes (plans list) and legacy single "plan" string
    plans = rec.get("plans") or _normalize_plans(rec.get("plan", "pro"))
    if not plans:
        plans = ["pro"]
    months = int(rec.get("duration_months", 1) or 1)
    days = months * 30
    expires_at = (dt.datetime.now() + dt.timedelta(days=days)).strftime("%Y-%m-%d")

    result = {
        "plan": ",".join(plans),
        "plans": plans,
        "duration_months": months,
        "expires_at": expires_at,
        "is_new_account": False,
        "key": "",
        "raw_key": "",
        "message": "",
    }
    msg_parts = []

    # ---- Browser app licenses (pro / pro_plus) ----
    # If both pro and pro_plus selected, grant the higher tier only once.
    app_plans = [p for p in plans if p in ("pro", "pro_plus")]
    if app_plans:
        grant_plan = "pro_plus" if "pro_plus" in app_plans else "pro"
        key = licensing.create_subscription_key(
            customer_name=name,
            customer_email=email,
            subscription_type="monthly",
            expires_at=expires_at,
            amount_paid=0,
            plan=grant_plan,
        )
        keys = persistence.load_license_keys()
        if key in keys:
            keys[key]["expires_at"] = expires_at
            keys[key]["subscription_type"] = f"promo_{months}m"
            keys[key]["amount_paid"] = 0
            keys[key]["promo_code"] = code
            persistence.save_license_keys(keys)
        result["key"] = key
        result["app_plan"] = grant_plan
        msg_parts.append(f"{grant_plan.replace('_', '+').title()} for {months} month(s)")

    # ---- API keys (can grant both starter and pro if both selected) ----
    lim = persistence.load_limits()
    api_keys_issued = []
    for api_plan in ("api_starter", "api_pro"):
        if api_plan not in plans:
            continue
        quota = int(lim.get(
            "API_PRO_QUOTA" if api_plan == "api_pro" else "API_STARTER_QUOTA",
            1000000 if api_plan == "api_pro" else 200000,
        ))
        created = api_keys.create_api_key(
            customer_name=name,
            customer_email=email,
            plan=api_plan,
            monthly_char_quota=quota,
        )
        raw_key = created.get("raw_key", "")
        all_api = persistence.load_api_keys()
        for ak in all_api:
            if ak.get("key_hash") == created["record"].get("key_hash"):
                ak["promo_code"] = code
                ak["expires_at"] = expires_at
                break
        persistence.save_api_keys(all_api)
        api_keys_issued.append({"plan": api_plan, "raw_key": raw_key})
        msg_parts.append(f"{api_plan} API for {months} month(s)")
        result["raw_key"] = raw_key
        result["api_plan"] = api_plan

    if api_keys_issued:
        result["api_keys"] = api_keys_issued

    result["message"] = "Free access granted: " + "; ".join(msg_parts) + "."
    if not msg_parts:
        return False, "This promo has no valid plans configured.", {}

    # ---- Account + email ----
    record, is_new = accounts.find_or_create_user(email, name)
    result["is_new_account"] = is_new

    def _email_all_keys():
        if result.get("key"):
            notifications.send_key_email(email, name, result["key"])
        lim_now = persistence.load_limits()
        for ak in (result.get("api_keys") or []):
            quota = int(lim_now.get(
                "API_PRO_QUOTA" if ak.get("plan") == "api_pro" else "API_STARTER_QUOTA",
                200000,
            ))
            notifications.send_api_key_email(email, name, ak["raw_key"], ak.get("plan", "api_starter"), quota)
        if not result.get("api_keys") and result.get("raw_key"):
            notifications.send_api_key_email(
                email, name, result["raw_key"],
                result.get("api_plan", "api_starter"),
                int(lim_now.get(
                    "API_PRO_QUOTA" if result.get("api_plan") == "api_pro" else "API_STARTER_QUOTA",
                    200000,
                )),
            )

    if is_new:
        import secrets
        token = secrets.token_urlsafe(32)
        expires = (dt.datetime.now() + dt.timedelta(hours=accounts.SET_PASSWORD_EXPIRES_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
        persistence.set_password_token(token, {
            "email": email,
            "expires_at": expires,
            "purpose": "set_password",
        })
        set_url = f"{site_url.rstrip('/')}/set-password?token={token}" if site_url else f"/set-password?token={token}"
        product_label = result.get("message") or "Promo plan"
        notifications.send_account_setup_email(email, name, set_url, product_label)
        _email_all_keys()
        result["message"] += " Check your email for the set-password link and your key(s)."
    else:
        _email_all_keys()
        result["message"] += " Your key is shown below (and emailed)."

    # ---- Record the redemption (atomic-ish: after success) ----
    redemption = {
        "id": str(uuid.uuid4()),
        "code": code,
        "type": "free",
        "email": email,
        "ip_hash": ip_hash,
        "fingerprint": fp,
        "plan": result.get("plan", ",".join(plans)),
        "duration_months": months,
        "key": result.get("key", ""),
        "redeemed_at": _now_iso(),
    }
    redemptions = persistence.load_promo_redemptions()
    redemptions.insert(0, redemption)
    persistence.save_promo_redemptions(redemptions)

    codes = persistence.load_promo_codes()
    if code in codes:
        codes[code]["uses_count"] = int(codes[code].get("uses_count", 0)) + 1
        persistence.save_promo_codes(codes)

    return True, result["message"], result


# ---- Simple rate limit for /redeem (in-process; sufficient at current scale)
_redeem_attempts: dict = {}  # key -> list of timestamps


def check_redeem_rate_limit(request, max_attempts: int = 8, window_seconds: int = 3600) -> str | None:
    """Returns error message if rate limited, else None."""
    import time
    ip_hash = hash_ip(get_client_ip(request))
    fp = get_browser_fingerprint(request)
    key = f"{ip_hash}:{fp}"
    now = time.time()
    window = _redeem_attempts.get(key, [])
    window = [t for t in window if now - t < window_seconds]
    if len(window) >= max_attempts:
        return "Too many redeem attempts. Please try again in an hour."
    window.append(now)
    _redeem_attempts[key] = window
    # Opportunistic cleanup
    if len(_redeem_attempts) > 5000:
        cutoff = now - window_seconds
        for k in list(_redeem_attempts.keys()):
            _redeem_attempts[k] = [t for t in _redeem_attempts[k] if t > cutoff]
            if not _redeem_attempts[k]:
                del _redeem_attempts[k]
    return None
