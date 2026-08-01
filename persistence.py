"""
persistence.py — generic GitHub-backed JSON read/write, ported from your
_gh_read / _gh_write / load_*_from_github / save_*_to_github functions.

Needs a GITHUB_TOKEN env var on Render with repo write access to
faisalchaudhary411/faisalchaudhary411.github.io (same repo your Streamlit
app used for blogs.json / limits.json / license_keys.json / etc.).
"""

import os
import json
import base64
import requests

GH_REPO = "faisalchaudhary411/faisalchaudhary411.github.io"
GH_BRANCH = "main"

GH_FILES = {
    "blogs": "blogs.json",
    "limits": "limits.json",
    "license_keys": "license_keys.json",
    "requests": "pro_requests.json",
    "cloned_voices": "cloned_voices.json",
    "usage": "usage_tracking.json",
}

DEFAULT_LIMITS = {
    "FREE_CHAR_LIMIT": 5000,           # max chars per SINGLE generation
    "FREE_MONTHLY_CHAR_QUOTA": 50000,  # cumulative chars across the whole month
    "FREE_DAILY_ACTIONS": 10,
    "FREE_BATCH_LIMIT": 5,
    "FREE_BATCH_MAX_LINES": 20,
    "FREE_PREVIEW_LIMIT": 5,
    "PRO_BATCH_MAX": 20,
    "FREE_VOICES_COUNT": 20,
    "PRO_PRICE_PKR": 840,
    "PRO_PRICE_LABEL": "840 PKR",
    "FREE_PRICE_LABEL": "$0",
    "CHECKOUT_URL": "",
    "FREE_FEATURES": "",
    "PRO_FEATURES": "",
    "AUTO_APPROVE_MANUAL": True,
    "MANUAL_GRACE_HOURS": 72,
}


def _token() -> str:
    return os.environ.get("GITHUB_TOKEN", "").strip()


def gh_read(filename: str):
    """Returns parsed JSON, or None if missing/misconfigured/error."""
    tok = _token()
    if not tok:
        return None
    try:
        h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(
            f"https://api.github.com/repos/{GH_REPO}/contents/{filename}?ref={GH_BRANCH}",
            headers=h, timeout=10,
        )
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
        return None
    except Exception:
        return None


def gh_write(filename: str, data, message: str) -> tuple:
    """Returns (ok: bool, error_msg: str)."""
    tok = _token()
    if not tok:
        return False, "GITHUB_TOKEN missing on this deployment."
    try:
        h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github.v3+json"}
        sha = None
        gr = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{filename}", headers=h, timeout=10)
        if gr.status_code == 200:
            sha = gr.json().get("sha")
        elif gr.status_code == 401:
            return False, "GitHub token is invalid or expired."
        elif gr.status_code == 403:
            return False, "GitHub token lacks write permission (needs repo scope)."

        encoded = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
        payload = {"message": message, "content": encoded, "branch": GH_BRANCH}
        if sha:
            payload["sha"] = sha
        pr = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{filename}", headers=h, json=payload, timeout=15)
        if pr.status_code in (200, 201):
            return True, ""
        return False, f"GitHub API error {pr.status_code}: {pr.text[:200]}"
    except Exception as e:
        return False, str(e)


# ---- typed convenience wrappers ----
def load_blogs() -> list:
    data = gh_read(GH_FILES["blogs"])
    return data if isinstance(data, list) else []


def save_blogs(posts: list) -> tuple:
    return gh_write(GH_FILES["blogs"], posts, "Update blogs.json via VoxCraft Admin")


def load_limits() -> dict:
    data = gh_read(GH_FILES["limits"])
    merged = DEFAULT_LIMITS.copy()
    if isinstance(data, dict):
        merged.update({k: data[k] for k in data if k in DEFAULT_LIMITS})
    return merged


def save_limits(limits: dict) -> tuple:
    return gh_write(GH_FILES["limits"], limits, "Update limits.json via Admin")


def load_license_keys() -> dict:
    data = gh_read(GH_FILES["license_keys"])
    return data if isinstance(data, dict) else {}


def save_license_keys(keys: dict) -> tuple:
    return gh_write(GH_FILES["license_keys"], keys, "Update license keys")


def load_requests() -> list:
    data = gh_read(GH_FILES["requests"])
    return data if isinstance(data, list) else []


def save_requests(reqs: list) -> tuple:
    return gh_write(GH_FILES["requests"], reqs, "Update pro requests")


def load_usage() -> dict:
    data = gh_read(GH_FILES["usage"])
    return data if isinstance(data, dict) else {}


def save_usage(data: dict) -> tuple:
    return gh_write(GH_FILES["usage"], data, "Update usage tracking")
