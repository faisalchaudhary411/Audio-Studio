"""
notifications.py — ported from _notify_admin / _send_key_email.
Resend is tried first (matches your other apps' pattern — SMTP is blocked on
Railway; unclear if Render blocks it too, so SMTP fallback is kept, just
untested on this specific host).
"""

import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _secret(key: str) -> str:
    return os.environ.get(key, "").strip()


def notify_admin_new_request(name, email, phone, req_id, payment_method="", txn_id="", screenshot_b64="", site_url=""):
    admin_link = f"{site_url.rstrip('/')}/admin/requests" if site_url else "/admin/requests"
    message_body = f"""New VoxCraft Pro Request!

Name: {name}
Email: {email}
Phone: {phone or 'N/A'}
Request ID: {req_id}
Payment: {payment_method or 'Not submitted'}
{'Txn/Ref ID: ' + txn_id if txn_id else ''}

Approve here: {admin_link}
"""
    notified = False
    errors = []
    resend_key = _secret("RESEND_API_KEY")
    admin_email = _secret("ADMIN_EMAIL")

    if resend_key and admin_email:
        try:
            pay_badge = f"<span style='background:#E8A93C;color:#000;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700'>{payment_method}</span>" if payment_method else "<span style='background:#555;color:#fff;padding:2px 10px;border-radius:20px;font-size:12px'>Not provided</span>"
            txn_row = f"<tr><td style='padding:6px 0;color:#888;font-size:13px'>Transaction ID</td><td style='padding:6px 0;color:#fff;font-size:13px;font-weight:700'>{txn_id}</td></tr>" if txn_id else ""
            admin_html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#101820;font-family:Arial,sans-serif">
<div style="max-width:520px;margin:0 auto;padding:24px 16px">
  <div style="background:#E8A93C;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px">
    <div style="color:#1A1204;font-size:18px;font-weight:800">New Pro Request</div>
    <div style="color:#1A1204;font-size:13px">VoxCraft Payment Received</div>
  </div>
  <div style="background:#182530;border-radius:12px;padding:20px;margin-bottom:16px">
    <table style="width:100%;border-collapse:collapse">
      <tr><td style="padding:6px 0;color:#888;font-size:13px">Name</td><td style="padding:6px 0;color:#fff;font-size:13px;font-weight:700">{name}</td></tr>
      <tr><td style="padding:6px 0;color:#888;font-size:13px">Email</td><td style="padding:6px 0;color:#E8A93C;font-size:13px">{email}</td></tr>
      <tr><td style="padding:6px 0;color:#888;font-size:13px">Phone</td><td style="padding:6px 0;color:#fff;font-size:13px">{phone or "—"}</td></tr>
      <tr><td style="padding:6px 0;color:#888;font-size:13px">Request ID</td><td style="padding:6px 0;color:#fff;font-size:11px;font-family:monospace">{req_id}</td></tr>
      <tr><td style="padding:6px 0;color:#888;font-size:13px">Payment</td><td style="padding:6px 0">{pay_badge}</td></tr>
      {txn_row}
    </table>
  </div>
  <div style="text-align:center;margin-bottom:16px;">
    <a href="{admin_link}" style="display:inline-block;background:#E8A93C;color:#1A1204;padding:10px 24px;border-radius:12px;font-weight:700;text-decoration:none;font-size:14px;">Review &amp; Approve →</a>
  </div>
  <div style="text-align:center;color:#444;font-size:11px">VoxCraft Admin</div>
</div></body></html>"""

            attachments = []
            if screenshot_b64:
                admin_html = admin_html.replace(
                    "</div></body></html>",
                    """<div style="margin-top:16px"><div style="color:#888;font-size:11px;margin-bottom:6px">PAYMENT SCREENSHOT</div><img src="cid:payment_screenshot" style="max-width:100%;border-radius:8px;border:1px solid #222"></div></div></body></html>""",
                )
                attachments = [{"filename": "payment_proof.jpg", "content": screenshot_b64, "content_type": "image/jpeg", "inline": True, "content_id": "payment_screenshot"}]

            payload = {"from": "VoxCraft <onboarding@resend.dev>", "to": [admin_email],
                       "subject": f"New Pro Payment — {name}", "html": admin_html, "text": message_body}
            if attachments:
                payload["attachments"] = attachments

            r = requests.post("https://api.resend.com/emails",
                               headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                               json=payload, timeout=20)
            if r.status_code in (200, 201):
                notified = True
            else:
                errors.append(f"Resend admin: {r.status_code} {r.text[:100]}")

            if email and notified:
                user_html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#101820;font-family:Arial,sans-serif">
<div style="max-width:520px;margin:0 auto;padding:24px 16px">
  <div style="background:#E8A93C;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px">
    <div style="color:#1A1204;font-size:18px;font-weight:800">Payment Received</div>
    <div style="color:#1A1204;font-size:13px">VoxCraft Pro — verification in progress</div>
  </div>
  <div style="background:#182530;border-radius:12px;padding:20px;margin-bottom:16px">
    <p style="color:#ccc;font-size:14px;margin:0 0 12px">Hi <strong style="color:#fff">{name}</strong>,</p>
    <p style="color:#ccc;font-size:14px;margin:0 0 12px">We received your payment for VoxCraft Pro. We'll verify and send your license key within a few hours.</p>
    <div style="background:#101820;border-radius:8px;padding:12px;margin:16px 0">
      <div style="color:#888;font-size:11px;margin-bottom:4px">Your Request ID</div>
      <div style="color:#E8A93C;font-size:13px;font-family:monospace;font-weight:700">{req_id}</div>
    </div>
  </div>
</div></body></html>"""
                try:
                    requests.post("https://api.resend.com/emails",
                                   headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                                   json={"from": "VoxCraft <onboarding@resend.dev>", "to": [email],
                                         "subject": "Payment Received — VoxCraft Pro", "html": user_html}, timeout=15)
                except Exception:
                    pass
        except Exception as e:
            errors.append(f"Resend: {e}")

    elif _secret("SMTP_HOST") and _secret("SMTP_USER") and _secret("SMTP_PASS") and admin_email:
        try:
            msg = MIMEMultipart()
            msg["From"] = _secret("SMTP_USER")
            msg["To"] = admin_email
            msg["Subject"] = f"VoxCraft Pro Request - {name}"
            msg.attach(MIMEText(message_body, "plain", "utf-8"))
            port = int(_secret("SMTP_PORT") or "587")
            if port == 465:
                import ssl
                server = smtplib.SMTP_SSL(_secret("SMTP_HOST"), port, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(_secret("SMTP_HOST"), port, timeout=15)
                server.starttls()
            server.login(_secret("SMTP_USER"), _secret("SMTP_PASS").replace(" ", ""))
            server.send_message(msg)
            server.quit()
            notified = True
        except Exception as e:
            errors.append(f"SMTP: {e}")

    return notified


def notify_admin_announcement_published(title, ann_type, message, site_url="") -> bool:
    """Sends the admin a copy of an announcement they just published — a
    confirmation/record, not a request for approval (unlike
    notify_admin_new_request). Opt-in from the admin/notifications form, so
    routine discount/update posts don't clutter the inbox unless wanted."""
    resend_key = _secret("RESEND_API_KEY")
    admin_email = _secret("ADMIN_EMAIL")
    if not (resend_key and admin_email):
        return False
    manage_link = f"{site_url.rstrip('/')}/admin/notifications" if site_url else "/admin/notifications"
    type_label = {"discount": "Discount", "update": "Update"}.get(ann_type, "Announcement")
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#101820;font-family:Arial,sans-serif">
<div style="max-width:520px;margin:0 auto;padding:24px 16px">
  <div style="background:#E8A93C;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px">
    <div style="color:#1A1204;font-size:18px;font-weight:800">{type_label} Published</div>
    <div style="color:#1A1204;font-size:13px">Now live on VoxCraft</div>
  </div>
  <div style="background:#182530;border-radius:12px;padding:20px;margin-bottom:16px">
    <div style="color:#E8A93C;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px">{type_label}</div>
    <div style="color:#fff;font-size:16px;font-weight:700;margin-bottom:8px">{title}</div>
    <div style="color:#ccc;font-size:14px;">{message}</div>
  </div>
  <div style="text-align:center;">
    <a href="{manage_link}" style="display:inline-block;background:#E8A93C;color:#1A1204;padding:10px 24px;border-radius:12px;font-weight:700;text-decoration:none;font-size:14px;">Manage announcements →</a>
  </div>
</div></body></html>"""
    try:
        r = requests.post("https://api.resend.com/emails",
                           headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                           json={"from": "VoxCraft <onboarding@resend.dev>", "to": [admin_email],
                                 "subject": f"{type_label} published — {title}", "html": html}, timeout=15)
        return r.status_code in (200, 201)
    except Exception:
        return False


def notify_contact_message(name, email, topic, message, req_id="", site_url="") -> bool:
    """Sends the admin a copy of a message submitted via the public /contact
    form. Mirrors notify_admin_new_request's Resend-first/SMTP-fallback
    pattern. Does not send anything to the visitor — support replies happen
    by email once the admin has read this."""
    resend_key = _secret("RESEND_API_KEY")
    admin_email = _secret("ADMIN_EMAIL")
    topic_label = (topic or "General").strip() or "General"
    plain_body = f"""New VoxCraft contact form message

Name: {name}
Email: {email}
Topic: {topic_label}
{'Request ID: ' + req_id if req_id else ''}

Message:
{message}
"""
    notified = False

    if resend_key and admin_email:
        try:
            safe_message = (message or "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#101820;font-family:Arial,sans-serif">
<div style="max-width:520px;margin:0 auto;padding:24px 16px">
  <div style="background:#E8A93C;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px">
    <div style="color:#1A1204;font-size:18px;font-weight:800">New Contact Message</div>
    <div style="color:#1A1204;font-size:13px">{topic_label}</div>
  </div>
  <div style="background:#182530;border-radius:12px;padding:20px;margin-bottom:16px">
    <table style="width:100%;border-collapse:collapse">
      <tr><td style="padding:6px 0;color:#888;font-size:13px">Name</td><td style="padding:6px 0;color:#fff;font-size:13px;font-weight:700">{name}</td></tr>
      <tr><td style="padding:6px 0;color:#888;font-size:13px">Email</td><td style="padding:6px 0;color:#E8A93C;font-size:13px">{email}</td></tr>
      <tr><td style="padding:6px 0;color:#888;font-size:13px">Topic</td><td style="padding:6px 0;color:#fff;font-size:13px">{topic_label}</td></tr>
    </table>
  </div>
  <div style="background:#182530;border-radius:12px;padding:20px;">
    <div style="color:#888;font-size:11px;margin-bottom:6px">MESSAGE</div>
    <div style="color:#fff;font-size:14px;line-height:1.6">{safe_message}</div>
  </div>
</div></body></html>"""
            r = requests.post("https://api.resend.com/emails",
                               headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                               json={"from": "VoxCraft <onboarding@resend.dev>", "to": [admin_email],
                                     "reply_to": email,
                                     "subject": f"Contact form — {topic_label} — {name}",
                                     "html": html, "text": plain_body}, timeout=15)
            notified = r.status_code in (200, 201)
        except Exception:
            notified = False

    if not notified and _secret("SMTP_HOST") and _secret("SMTP_USER") and _secret("SMTP_PASS") and admin_email:
        try:
            msg = MIMEMultipart()
            msg["From"] = _secret("SMTP_USER")
            msg["To"] = admin_email
            msg["Reply-To"] = email
            msg["Subject"] = f"VoxCraft contact form - {topic_label} - {name}"
            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
            port = int(_secret("SMTP_PORT") or "587")
            if port == 465:
                import ssl
                server = smtplib.SMTP_SSL(_secret("SMTP_HOST"), port, context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(_secret("SMTP_HOST"), port, timeout=15)
                server.starttls()
            server.login(_secret("SMTP_USER"), _secret("SMTP_PASS").replace(" ", ""))
            server.send_message(msg)
            server.quit()
            notified = True
        except Exception:
            notified = False

    return notified


def send_key_email(user_email: str, user_name: str, license_key: str) -> bool:
    resend_key = _secret("RESEND_API_KEY")
    if not resend_key:
        return False
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#101820;font-family:Arial,sans-serif">
<div style="max-width:520px;margin:0 auto;padding:24px 16px">
  <div style="background:#E8A93C;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px">
    <div style="color:#1A1204;font-size:18px;font-weight:800">Welcome to VoxCraft Pro</div>
  </div>
  <div style="background:#182530;border-radius:12px;padding:20px;margin-bottom:16px">
    <p style="color:#ccc;font-size:14px;margin:0 0 12px">Hi <strong style="color:#fff">{user_name}</strong>,</p>
    <p style="color:#ccc;font-size:14px;margin:0 0 12px">Your license key is below — enter it on the Studio page to activate Pro.</p>
    <div style="background:#101820;border-radius:8px;padding:14px;margin:16px 0;text-align:center">
      <div style="color:#E8A93C;font-size:15px;font-family:monospace;font-weight:700;letter-spacing:1px">{license_key}</div>
    </div>
  </div>
</div></body></html>"""
    try:
        r = requests.post("https://api.resend.com/emails",
                           headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                           json={"from": "VoxCraft <onboarding@resend.dev>", "to": [user_email],
                                 "subject": "Your VoxCraft Pro License Key", "html": html}, timeout=15)
        return r.status_code in (200, 201)
    except Exception:
        return False


def send_api_key_email(customer_email: str, customer_name: str, raw_key: str, plan: str, monthly_char_quota: int) -> bool:
    """Delivers a newly-issued developer API key. Same Resend pattern as
    send_key_email above. Called once, right after admin_api_keys creates
    the key — this is the ONLY time the raw key is ever available to send,
    since it's hashed before being stored (see api_keys.py)."""
    resend_key = _secret("RESEND_API_KEY")
    if not resend_key:
        return False
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#101820;font-family:Arial,sans-serif">
<div style="max-width:560px;margin:0 auto;padding:24px 16px">
  <div style="background:#E8A93C;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px">
    <div style="color:#1A1204;font-size:18px;font-weight:800">Your VoxCraft API Key</div>
    <div style="color:#1A1204;font-size:13px">Plan: {plan} — {monthly_char_quota:,} characters/month</div>
  </div>
  <div style="background:#182530;border-radius:12px;padding:20px;margin-bottom:16px">
    <p style="color:#ccc;font-size:14px;margin:0 0 12px">Hi <strong style="color:#fff">{customer_name}</strong>,</p>
    <p style="color:#ccc;font-size:14px;margin:0 0 12px">Your VoxCraft developer API key is below. Store it securely — for security, we can't show it to you again after this email; if it's lost, a new key needs to be issued.</p>
    <div style="background:#101820;border-radius:8px;padding:14px;margin:16px 0;text-align:center;word-break:break-all;">
      <div style="color:#E8A93C;font-size:14px;font-family:monospace;font-weight:700;">{raw_key}</div>
    </div>
    <p style="color:#888;font-size:12px;margin:16px 0 4px;">Quick start:</p>
    <div style="background:#101820;border-radius:8px;padding:14px;color:#9cdcfe;font-size:12px;font-family:monospace;white-space:pre-wrap;">curl -X POST https://voxcraft.site/api/v1/tts \\
  -H "Authorization: Bearer {raw_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{"text": "Hello world", "voice_id": "en-US-AvaNeural"}}' \\
  --output speech.mp3</div>
  </div>
</div></body></html>"""
    try:
        r = requests.post("https://api.resend.com/emails",
                           headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                           json={"from": "VoxCraft <onboarding@resend.dev>", "to": [customer_email],
                                 "subject": "Your VoxCraft API Key", "html": html}, timeout=15)
        return r.status_code in (200, 201)
    except Exception:
        return False
