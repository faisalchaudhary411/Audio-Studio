#!/usr/bin/env python3
"""
backup_db.py — nightly SQLite backup, run via cron. Two layers of
protection against losing the DB (currently: zero backups at all — one bad
`git pull`, disk failure, or accidental `rm` wipes every customer's
license key, API key, and account with no way to recover):

  1. LOCAL rotating copies in data/backups/, using sqlite3's built-in
     online backup API (Connection.backup()) rather than a plain file
     copy — a plain `cp` mid-write can copy a half-written/corrupted file
     if the app happens to be writing at that exact moment; the backup
     API is explicitly designed to be safe against a live database.
  2. OFF-VPS copy: the compressed backup is emailed to ADMIN_EMAIL via
     Resend — the same API this app already uses for every other
     notification — as an attachment. No new account or service to sign
     up for. Skipped (logged, not crashed) if the compressed file is too
     large for an email attachment (~15MB) or if RESEND_API_KEY/
     ADMIN_EMAIL aren't set — the local copy still happens either way, so
     a missing env var never means "no backup at all."

Local backups older than BACKUP_RETENTION_DAYS are pruned so this doesn't
grow unbounded on VPS disk.

DEPLOY — add to crontab (`crontab -e`) to run nightly, e.g. at 3am:

    0 3 * * * cd /home/deploy/voxcraft && /usr/bin/python3 backup_db.py >> /home/deploy/voxcraft/data/backup.log 2>&1

Adjust the path to wherever app.py actually lives on your VPS, and to your
venv's python3 if you use one (e.g. /home/deploy/voxcraft/venv/bin/python3
instead of /usr/bin/python3).

To test it works right now, without waiting for cron, just run it by hand:
    cd /home/deploy/voxcraft && python3 backup_db.py
and check both the printed output and your ADMIN_EMAIL inbox.
"""
import os
import sys
import gzip
import shutil
import sqlite3
import base64
import datetime as dt

import requests

import persistence

BACKUP_DIR = os.path.join(os.path.dirname(persistence.DB_PATH), "backups")
BACKUP_RETENTION_DAYS = 14
# ~15MB of actual file — base64 encoding inflates that by ~33% before it
# even reaches Resend, and most providers cap total message size around
# 20-25MB, so this leaves real headroom rather than cutting it close.
MAX_EMAIL_ATTACHMENT_BYTES = 15 * 1024 * 1024

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip()
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "VoxCraft <noreply@voxcraft.site>").strip()


def _log(msg):
    print(f"[{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def create_backup() -> str:
    """Returns the path to a fresh, gzip-compressed backup file."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    raw_path = os.path.join(BACKUP_DIR, f"voxcraft-{timestamp}.db")
    gz_path = raw_path + ".gz"

    source = sqlite3.connect(persistence.DB_PATH)
    dest = sqlite3.connect(raw_path)
    with dest:
        source.backup(dest)
    source.close()
    dest.close()

    with open(raw_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.remove(raw_path)
    return gz_path


def prune_old_backups():
    cutoff = dt.datetime.now() - dt.timedelta(days=BACKUP_RETENTION_DAYS)
    if not os.path.isdir(BACKUP_DIR):
        return
    for fname in os.listdir(BACKUP_DIR):
        fpath = os.path.join(BACKUP_DIR, fname)
        try:
            mtime = dt.datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
                _log(f"Pruned old backup: {fname}")
        except OSError:
            continue


def email_backup(gz_path: str) -> bool:
    if not RESEND_API_KEY or not ADMIN_EMAIL:
        _log("RESEND_API_KEY or ADMIN_EMAIL not set — skipping off-VPS email copy (local backup still saved).")
        return False
    size = os.path.getsize(gz_path)
    if size > MAX_EMAIL_ATTACHMENT_BYTES:
        _log(f"Backup is {size / 1024 / 1024:.1f}MB — too large to email safely. "
             f"Local copy is still saved at {gz_path}; consider offsite cloud storage instead once the DB grows this big.")
        return False
    with open(gz_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={
                "from": RESEND_FROM_EMAIL,
                "to": [ADMIN_EMAIL],
                "subject": f"VoxCraft DB backup — {dt.datetime.now().strftime('%Y-%m-%d')}",
                "html": "<p>Nightly database backup attached. Keep this somewhere safe — it contains customer emails, hashed passwords, and license/API key data.</p>",
                "attachments": [{"filename": os.path.basename(gz_path), "content": content_b64}],
            },
            timeout=30,
        )
        if r.status_code in (200, 201):
            _log(f"Backup emailed to {ADMIN_EMAIL} ({size / 1024:.0f}KB).")
            return True
        _log(f"Resend returned {r.status_code}: {r.text[:300]}")
        return False
    except Exception as e:
        _log(f"Email send failed: {e}")
        return False


if __name__ == "__main__":
    _log("Starting backup...")
    try:
        gz_path = create_backup()
        _log(f"Local backup saved: {gz_path}")
    except Exception as e:
        _log(f"BACKUP FAILED: {e}")
        sys.exit(1)
    email_backup(gz_path)
    prune_old_backups()
    _log("Done.")
