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
  4. The same txn_id or the same screenshot (exact byte match) can't be used
     on more than one live request — catches the same payment (or the same
     screenshot) being claimed for multiple signups. A duplicate on either
     forces manual review even if auto-approval is enabled.
  5. A device is rate-limited to a few open (pending/payment_pending)
     requests at once, so the review queue can't be flooded.
  6. The screenshot itself is now kept on the request record (not just
     relayed once via the admin notification email), so /admin/requests can
     still show it whenever it's actually reviewed — previously the ONLY
     copy was whatever landed in that one email.
  7. If tesseract-ocr is installed on the server (`apt install tesseract-ocr`
     — optional, everything above works without it), the screenshot is OCR'd
     and cross-checked: does the typed txn_id actually appear IN the image,
     and does the plan's price appear too? A txn_id that doesn't show up in
     the screenshot at all is treated the same as a duplicate — forces
     manual review. Amount mismatch is surfaced to admin as a flag only,
     not a hard gate, since currency formatting varies too much across
     banking apps to risk blocking a genuine customer on a false negative.

None of this is real payment verification against EasyPaisa/JazzCash/the
bank — that would need a merchant API integration this app doesn't have.
What's here is deliberately the next-best thing: closing the specific gaps
that let obviously-fake submissions (blank txn_id, reused screenshot, reused
transaction ID, no real image at all) sail through unnoticed, so admin
review time goes toward the ambiguous cases that actually need a human
looking at them.

Controlled by admin-configurable AUTO_APPROVE_MANUAL / MANUAL_GRACE_HOURS in
/admin/limits (GitHub-backed, same as everything else) — not an env var, so
you can flip it without redeploying.
"""

import time
import random
import re
import hashlib
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


# Statuses that count as "this evidence is already live" for duplicate
# checks below — deliberately excludes 'rejected': if a request was
# rejected (e.g. wrong plan selected, blurry image), the same real
# transaction ID/screenshot should still be resubmittable once fixed,
# rather than being permanently blacklisted by its own rejected attempt.
_LIVE_STATUSES = ("pending", "payment_pending", "approved")


def _txn_id_is_duplicate(txn_id: str, exclude_req_id: str = "") -> bool:
    """The single most useful fraud check here: a genuine transaction ID
    is unique to one real payment. Seeing the same txn_id on a second
    request means either the same payment is being claimed twice, or the
    ID was never real to begin with (typed/copied from somewhere else)."""
    txn_id = (txn_id or "").strip().lower()
    if not txn_id:
        return False
    for r in persistence.load_requests():
        if r.get("id") == exclude_req_id:
            continue
        if r.get("status") in _LIVE_STATUSES and (r.get("txn_id") or "").strip().lower() == txn_id:
            return True
    return False


def _screenshot_sha256(screenshot_b64: str) -> str:
    if not screenshot_b64:
        return ""
    try:
        import base64
        raw = base64.b64decode(screenshot_b64, validate=True)
        return hashlib.sha256(raw).hexdigest()
    except Exception:
        return ""


def _screenshot_is_duplicate(screenshot_hash: str, exclude_req_id: str = "") -> bool:
    """Catches the other common trick: reusing ONE real payment screenshot
    (a friend's, or an old one of your own) across several signups with
    different names/emails/txn_ids typed in around it. Exact-hash match
    only — deliberately not a perceptual/fuzzy hash, since a fuzzy match
    risks flagging two different customers' genuinely different but
    visually similar screenshots (same banking app UI) as fraud."""
    if not screenshot_hash:
        return False
    for r in persistence.load_requests():
        if r.get("id") == exclude_req_id:
            continue
        if r.get("status") in _LIVE_STATUSES and r.get("screenshot_sha256") == screenshot_hash:
            return True
    return False


RATE_LIMIT_MAX_PENDING_PER_IP = 3
RATE_LIMIT_WINDOW_HOURS = 24


def _rate_limited(ip_hash: str) -> bool:
    """Caps how many still-open requests one device can have in flight at
    once — stops the admin review queue from being flooded by someone
    spamming the form (accidentally or as a denial-of-service against your
    attention), without touching genuine customers who'd only ever submit
    once per purchase."""
    if not ip_hash:
        return False
    cutoff = dt.datetime.now() - dt.timedelta(hours=RATE_LIMIT_WINDOW_HOURS)
    count = 0
    for r in persistence.load_requests():
        if r.get("ip") != ip_hash or r.get("status") not in ("pending", "payment_pending"):
            continue
        try:
            if dt.datetime.strptime(r.get("date", ""), "%Y-%m-%d %H:%M") < cutoff:
                continue
        except Exception:
            pass
        count += 1
    return count >= RATE_LIMIT_MAX_PENDING_PER_IP


def _ocr_extract_text(screenshot_b64: str) -> str:
    """Best-effort OCR of the uploaded screenshot. Returns '' — treated as
    'inconclusive', never as a failure — whenever pytesseract or the
    underlying tesseract-ocr system binary isn't installed (this whole
    check quietly no-ops on a deploy that hasn't run
    `apt install tesseract-ocr` yet, same graceful-degradation pattern
    RESEND_API_KEY unset already uses elsewhere), or the image is too
    blurry/cropped/low-contrast for OCR to read anything. A genuine
    payment screenshot that happens to OCR poorly should never be treated
    the same as a duplicate/forged one — see how the two results are used
    differently below."""
    if not screenshot_b64:
        return ""
    try:
        import pytesseract
        from PIL import Image
        import io
        import base64
        raw = base64.b64decode(screenshot_b64, validate=True)
        img = Image.open(io.BytesIO(raw))
        return pytesseract.image_to_string(img).lower()
    except Exception:
        return ""


def _digits_only(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _ocr_txn_id_found(ocr_text: str, txn_id: str) -> bool:
    """Digits-only substring match — OCR on a phone screenshot regularly
    mangles surrounding punctuation/spacing/dashes around a reference
    number but is usually reliable on the digit sequence itself, which is
    the part that actually identifies the transaction."""
    txn_digits = _digits_only(txn_id)
    if len(txn_digits) < 4:  # too short to search for without risking false positives on a common short number elsewhere in the image
        return False
    return txn_digits in _digits_only(ocr_text)


def _ocr_amount_found(ocr_text: str, expected_amount) -> bool:
    """Exact whole-number token match (not substring) — deliberately
    stricter than the txn_id check above, since a substring match on a
    plain amount like '840' would trivially false-positive against phone
    numbers, dates, or any other number sharing that digit sequence."""
    if not expected_amount:
        return False
    try:
        target = str(int(expected_amount))
    except Exception:
        return False
    return target in re.findall(r"\d+", ocr_text)


def submit_pro_request(request, name, email, phone="", payment_method="", txn_id="", screenshot_b64="", plan="pro"):
    reqs = persistence.load_requests()
    req_id = f"REQ-{int(time.time())}-{random.randint(1000, 9999)}"
    ip_hash = hash_ip(get_client_ip(request))
    plan = plan if plan in ("pro", "pro_plus") else "pro"

    if _rate_limited(ip_hash):
        return {"success": False,
                "error": "You already have a few payment requests awaiting review. Please wait for those to be processed before submitting another."}

    limits = persistence.load_limits()
    auto_approve_enabled = limits.get("AUTO_APPROVE_MANUAL", False)
    grace_hours = limits.get("MANUAL_GRACE_HOURS", 72)

    screenshot_hash = _screenshot_sha256(screenshot_b64)
    duplicate_txn = _txn_id_is_duplicate(txn_id)
    duplicate_screenshot = _screenshot_is_duplicate(screenshot_hash)

    # OCR cross-check: does the txn_id the customer typed actually appear
    # IN the screenshot they uploaded, and does the plan's price appear
    # too? ocr_available is False (not "failed") whenever tesseract isn't
    # installed or nothing readable was found — that case is deliberately
    # excluded from the auto-approval gate below rather than treated as a
    # mismatch, so a server without tesseract set up just behaves exactly
    # as it did before this was added.
    expected_amount = limits.get("PRO_PLUS_PRICE_PKR" if plan == "pro_plus" else "PRO_PRICE_PKR", 0)
    ocr_text = _ocr_extract_text(screenshot_b64)
    ocr_available = bool(ocr_text.strip())
    ocr_txn_match = _ocr_txn_id_found(ocr_text, txn_id) if ocr_available else False
    ocr_amount_match = _ocr_amount_found(ocr_text, expected_amount) if ocr_available else False

    auto_approved = False
    internal_key = None

    # Same conditions as before, PLUS: neither the txn_id nor the
    # screenshot may already be in use by another live request, AND — if
    # OCR is available and found readable text at all — the typed txn_id
    # must actually appear in that text. Amount match is deliberately NOT
    # a gate here (currency formatting varies too much across banking
    # apps to risk blocking a genuine customer on a false negative) — it's
    # surfaced to admin as an informational flag instead, see below.
    if (auto_approve_enabled and txn_id.strip() and _is_valid_image(screenshot_b64)
            and not _device_already_auto_approved(ip_hash)
            and not duplicate_txn and not duplicate_screenshot
            and not (ocr_available and not ocr_txn_match)):
        internal_key = licensing.create_subscription_key(
            name.strip(), email.strip(), subscription_type="grace",
            expires_in_hours=grace_hours, plan=plan,
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
        # Kept in the request record itself now (not just relayed once via
        # the admin notification email) so it's still reviewable later in
        # /admin/requests — previously the ONLY copy was whatever landed in
        # that one email, gone from the app itself the moment it was sent.
        "screenshot_b64": screenshot_b64,
        "screenshot_sha256": screenshot_hash,
        "duplicate_txn": duplicate_txn,
        "duplicate_screenshot": duplicate_screenshot,
        "ocr_available": ocr_available,
        "ocr_txn_match": ocr_txn_match,
        "ocr_amount_match": ocr_amount_match,
        "auto_approved": auto_approved,
        "grace_expires": (dt.datetime.now() + dt.timedelta(hours=grace_hours)).strftime("%Y-%m-%d %H:%M") if auto_approved else "",
        "plan_requested": plan,
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
