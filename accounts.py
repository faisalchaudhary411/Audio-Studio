"""
Accounts for PAID customers only — Pro/Pro+ app subscribers and Developer
API Starter/Pro customers. Free tier (both the app's free voices and the
API's free key) stays fully anonymous/keyless by design; nothing in this
module is ever reachable from those flows.

Deliberately NOT the source of truth for Pro/API access — licensing.py's
license keys and api_keys.py's API keys still are, unchanged. An account
is a *login wrapper* around those: logging in looks up the customer's
existing key(s) by email and hands them back, rather than replacing the
key-based checks used everywhere else in the app. This means nothing
downstream (is_pro(), get_plan(), the API's Bearer-token auth) needed to
change to add this.

No self-serve "sign up" — accounts are created automatically the moment
someone pays (Freemius callback, or admin's manual bank-transfer approval),
carrying no password yet, and the customer sets one via an emailed link.
Same token mechanism (password_tokens table, single-use, expiring) powers
both that initial "set your password" link and the ordinary "forgot
password" reset link — the only difference is which notification email
gets sent.
"""
import secrets
import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash

import persistence

TOKEN_BYTES = 32
SET_PASSWORD_EXPIRES_HOURS = 72   # generous — this arrives right after a purchase, but people don't always open email same-day
RESET_PASSWORD_EXPIRES_HOURS = 1  # tighter — this one grants immediate account access if intercepted


def find_user(email: str) -> dict:
    """Returns {} if no account exists for this email — callers check
    truthiness, same convention as persistence.get_login_attempts()."""
    if not email:
        return {}
    return persistence.get_user(email)


def find_or_create_user(email: str, name: str) -> tuple:
    """Called at the moment of payment (fs_callback, fs_callback_api, or
    the admin manual-approval action) — never from a self-serve signup
    form, since there isn't one. Idempotent: a customer renewing, or
    upgrading Starter→Pro, hits this again and gets their existing account
    back untouched (password intact) rather than a second account or a
    wiped password. Returns (record, is_new) so the caller knows whether
    to send a "welcome, set your password" email or skip it.
    """
    email = (email or "").strip().lower()
    existing = find_user(email)
    if existing:
        return existing, False
    record = {
        "email": email,
        "name": name or "Customer",
        "password_hash": "",  # unset until they use a set-password link
        "created": dt.datetime.now().strftime("%Y-%m-%d"),
    }
    persistence.set_user(email, record)
    return record, True


def set_password(email: str, raw_password: str) -> bool:
    email = (email or "").strip().lower()
    record = find_user(email)
    if not record:
        return False
    record["password_hash"] = generate_password_hash(raw_password)
    persistence.set_user(email, record)
    return True


def verify_login(email: str, raw_password: str) -> dict:
    """Returns the user record on success, {} on any failure (no account,
    no password set yet, wrong password) — deliberately the same shape for
    all three so the login route can't leak which case it was."""
    record = find_user(email)
    if not record or not record.get("password_hash"):
        return {}
    if not check_password_hash(record["password_hash"], raw_password):
        return {}
    return record


def issue_token(email: str, purpose: str) -> str:
    """purpose is 'set' (initial password, from a fresh account) or
    'reset' (forgot-password) — same token shape, different expiry and
    different email copy sent by the caller."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    hours = SET_PASSWORD_EXPIRES_HOURS if purpose == "set" else RESET_PASSWORD_EXPIRES_HOURS
    expires_at = (dt.datetime.now() + dt.timedelta(hours=hours)).isoformat()
    persistence.set_password_token(token, {
        "email": email.strip().lower(), "purpose": purpose,
        "expires_at": expires_at, "used": False,
    })
    return token


def consume_token(token: str) -> dict:
    """Validates + immediately marks the token used (single-use — a set/
    reset link can't be replayed after it's been opened once), and
    returns {"email":..., "purpose":...} on success or {} on any failure
    (unknown token, expired, already used)."""
    record = persistence.get_password_token(token)
    if not record or record.get("used"):
        return {}
    try:
        expired = dt.datetime.fromisoformat(record["expires_at"]) < dt.datetime.now()
    except Exception:
        expired = True
    if expired:
        return {}
    record["used"] = True
    persistence.set_password_token(token, record)
    return {"email": record["email"], "purpose": record["purpose"]}


def update_profile(email: str, *, name: str = None, username: str = None,
                   phone: str = None, avatar_url: str = None) -> dict:
    """Update profile fields on the user JSON record. Returns updated record or {}."""
    email = (email or "").strip().lower()
    record = find_user(email)
    if not record:
        return {}
    if name is not None:
        record["name"] = (name or "").strip()[:80] or record.get("name") or "Customer"
    if username is not None:
        u = (username or "").strip().lstrip("@")[:32]
        # allow letters, numbers, underscore, dot
        import re
        u = re.sub(r"[^a-zA-Z0-9._]", "", u)
        record["username"] = u
    if phone is not None:
        record["phone"] = (phone or "").strip()[:24]
    if avatar_url is not None:
        record["avatar_url"] = (avatar_url or "").strip()[:500]
    persistence.set_user(email, record)
    return record


def change_password(email: str, current_password: str, new_password: str) -> tuple:
    """Returns (ok: bool, error: str)."""
    email = (email or "").strip().lower()
    record = find_user(email)
    if not record or not record.get("password_hash"):
        return False, "Account not found or password not set yet."
    if not check_password_hash(record["password_hash"], current_password or ""):
        return False, "Current password is incorrect."
    if len(new_password or "") < 8:
        return False, "New password must be at least 8 characters."
    if current_password == new_password:
        return False, "New password must be different from the current one."
    record["password_hash"] = generate_password_hash(new_password)
    persistence.set_user(email, record)
    return True, ""


def username_taken(username: str, except_email: str = "") -> bool:
    """Best-effort uniqueness check across users table."""
    username = (username or "").strip().lstrip("@").lower()
    if not username:
        return False
    try:
        users = persistence.list_users() if hasattr(persistence, "list_users") else []
    except Exception:
        users = []
    except_email = (except_email or "").strip().lower()
    for u in users:
        if (u.get("email") or "").lower() == except_email:
            continue
        if (u.get("username") or "").lower() == username:
            return True
    return False
