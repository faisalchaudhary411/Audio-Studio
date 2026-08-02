"""
pro_requests.py — manual bank-transfer flow (EasyPaisa/JazzCash/HBL), now with
optional instant auto-approval (matching QalamStudio's flow, with the same
lessons already applied rather than discovered later):

  1. Requires an actual transaction/reference ID, not just any upload.
  2. The uploaded "screenshot" must actually decode as a real image (Pillow) —
     doesn't verify it's a genuine payment screenshot, but filters out blank
     files, corrupted uploads, or non-image files.
  3. One auto-approval per device, ever — tracked via the same IP hash used
     for device-binding elsewhere, so the same person can't resubmit with a
     new email each time for a fresh grace-period Pro window indefinitely.

Controlled by admin-configurable AUTO_APPROVE_MANUAL / MANUAL_GRACE_HOURS in
/admin/limits (GitHub-backed, same as everything else) — not an env var, so
you can flip it without redeploying.
"""

import time
import random
import datetime as dt

import persistence
import licensing
import notifications
from usage_tracking import get_client_ip, hash_ip


def _is_valid_image(b64_data: str) -> bool:
    if not b64_data:
        return False
    try:
        from PIL import Image
        import io
        import base64
        raw = base64.b64decode(b64_data, validate=True)
        img = Image.open(io.BytesIO(raw))
        img.verify()
        return True
    except Exception:
        return False


def _device_already_auto_approved(ip_hash: str) -> bool:
    if not ip_hash:
        return False
    for r in persistence.load_requests():
        if r.get("auto_approved") and r.get("ip") == ip_hash:
            return True
    return False


def submit_pro_request(request, name, email, phone="", payment_method="", txn_id="", screenshot_b64=""):
    reqs = persistence.load_requests()
    req_id = f"REQ-{int(time.time())}-{random.randint(1000, 9999)}"
    ip_hash = hash_ip(get_client_ip(request))

    limits = persistence.load_limits()
    auto_approve_enabled = limits.get("AUTO_APPROVE_MANUAL", False)
    grace_hours = limits.get("MANUAL_GRACE_HOURS", 72)

    auto_approved = False
    internal_key = None

    if (auto_approve_enabled and txn_id.strip() and _is_valid_image(screenshot_b64)
            and not _device_already_auto_approved(ip_hash)):
        internal_key = licensing.create_subscription_key(
            name.strip(), email.strip(), subscription_type="grace",
            expires_in_hours=grace_hours,
        )
        # Immediately bind this key to the CURRENT device/session so the
        # customer gets instant access on the browser they're using right
        # now — not just an emailed key they'd have to separately activate.
        licensing.activate_vox_license(internal_key, request)
        auto_approved = True

    new_req = {
        "id": req_id,
        "name": name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "status": "approved" if auto_approved else ("payment_pending" if payment_method else "pending"),
        "date": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "key_assigned": internal_key or "",
        "ip": ip_hash,
        "notified": False,
        "payment_method": payment_method,
        "txn_id": txn_id.strip(),
        "has_screenshot": bool(screenshot_b64),
        "auto_approved": auto_approved,
        "grace_expires": (dt.datetime.now() + dt.timedelta(hours=grace_hours)).strftime("%Y-%m-%d %H:%M") if auto_approved else "",
    }
    reqs.insert(0, new_req)
    notified = notifications.notify_admin_new_request(name, email, phone, req_id,
                                                        payment_method=payment_method,
                                                        txn_id=txn_id, screenshot_b64=screenshot_b64,
                                                        site_url=request.url_root)
    new_req["notified"] = notified
    if auto_approved and email:
        notifications.send_key_email(email, name, internal_key)

    ok, err = persistence.save_requests(reqs)
    if ok:
        return {
            "success": True, "id": req_id, "notified": notified,
            "auto_approved": auto_approved, "license_key": internal_key,
            "grace_hours": grace_hours if auto_approved else None,
        }
    return {"success": False, "error": err}


def approve_request(req_id: str, license_key: str) -> bool:
    reqs = persistence.load_requests()
    user_email = user_name = None
    for req in reqs:
        if req["id"] == req_id:
            req["status"] = "approved"
            req["key_assigned"] = license_key
            req["approved_date"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            user_email = req.get("email")
            user_name = req.get("name", "Pro User")
            break
    persistence.save_requests(reqs)
    if user_email:
        notifications.send_key_email(user_email, user_name, license_key)
        return True
    return False


def reject_request(req_id: str) -> bool:
    reqs = persistence.load_requests()
    for req in reqs:
        if req["id"] == req_id:
            req["status"] = "rejected"
            req["rejected_date"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            persistence.save_requests(reqs)
            return True
    return False
