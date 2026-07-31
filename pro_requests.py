"""
pro_requests.py — ported from submit_pro_request / approve_request / reject_request.
This is the manual bank-transfer flow (EasyPaisa/JazzCash/HBL) — the customer
pays manually, submits proof here, you approve it in /admin, and they get an
emailed license key.
"""

import time
import random
import datetime as dt

import persistence
import licensing
import notifications
from usage_tracking import get_client_ip, hash_ip


def submit_pro_request(request, name, email, phone="", payment_method="", txn_id="", screenshot_b64=""):
    reqs = persistence.load_requests()
    req_id = f"REQ-{int(time.time())}-{random.randint(1000, 9999)}"
    new_req = {
        "id": req_id,
        "name": name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "status": "payment_pending" if payment_method else "pending",
        "date": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "key_assigned": "",
        "ip": hash_ip(get_client_ip(request)),
        "notified": False,
        "payment_method": payment_method,
        "txn_id": txn_id.strip(),
        "has_screenshot": bool(screenshot_b64),
    }
    reqs.insert(0, new_req)
    notified = notifications.notify_admin_new_request(name, email, phone, req_id,
                                                        payment_method=payment_method,
                                                        txn_id=txn_id, screenshot_b64=screenshot_b64)
    new_req["notified"] = notified
    ok, err = persistence.save_requests(reqs)
    if ok:
        return {"success": True, "id": req_id, "notified": notified}
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
