"""
migrate_to_sqlite.py — ONE-TIME migration from the old GitHub-JSON storage
into the new SQLite database (persistence.py).

WHY THIS MATTERS: your existing license_keys.json has real customers who
already paid. Deploying the new SQLite-backed app.py without running this
first means the app starts with an EMPTY database — every existing Pro
customer's key would suddenly show as invalid. Run this BEFORE restarting
the app with the new code, not after.

Usage (on the VPS, as the deploy user, from the app directory):
    cd ~/voxcraft
    source venv/bin/activate
    python3 deploy/migrate_to_sqlite.py

Requires GITHUB_TOKEN to still be set in .env at the time you run this
(it's only needed for this one-time read — you can remove it from .env
afterward, the new persistence.py doesn't use it for anything).

Safe to re-run: each table is fully replaced with what's fetched from
GitHub, so running this twice just re-syncs rather than duplicating data.
It does NOT delete anything from GitHub — your JSON files stay there
untouched as a historical backup even after this runs.
"""

import os
import sys
import json
import base64
import requests

# Make sure we're running from the app directory so `persistence` resolves.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

try:
    import persistence  # the NEW sqlite-backed module
except ImportError:
    print("ERROR: could not import persistence.py — run this from your app directory:")
    print("  cd ~/voxcraft && python3 deploy/migrate_to_sqlite.py")
    sys.exit(1)

GH_REPO = "faisalchaudhary411/faisalchaudhary411.github.io"
GH_BRANCH = "main"
GH_FILES = {
    "blogs": "blogs.json",
    "limits": "limits.json",
    "license_keys": "license_keys.json",
    "requests": "pro_requests.json",
    "usage": "usage_tracking.json",
}


def _token() -> str:
    return os.environ.get("GITHUB_TOKEN", "").strip()


def gh_read(filename: str):
    tok = _token()
    if not tok:
        return None
    try:
        h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(
            f"https://api.github.com/repos/{GH_REPO}/contents/{filename}?ref={GH_BRANCH}",
            headers=h, timeout=15,
        )
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
        print(f"  WARNING: GitHub returned {r.status_code} for {filename} — skipping this file.")
        return None
    except Exception as e:
        print(f"  WARNING: failed to fetch {filename}: {e}")
        return None


def migrate():
    if not _token():
        print("ERROR: GITHUB_TOKEN is not set. Add it to .env temporarily to run this migration,")
        print("       then you can remove it afterward — the new code doesn't need it.")
        sys.exit(1)

    print("=== Migrating GitHub-JSON data into SQLite ===")
    print(f"DB path: {persistence.DB_PATH}")
    print()

    # --- license keys (most important — real customer data) ---
    print("Fetching license_keys.json...")
    keys = gh_read(GH_FILES["license_keys"])
    if isinstance(keys, dict) and keys:
        ok, err = persistence.save_license_keys(keys)
        if ok:
            print(f"  Migrated {len(keys)} license key(s). OK")
        else:
            print(f"  FAILED to save license keys: {err}")
            sys.exit(1)
    else:
        print("  No license keys found (empty or missing file) — nothing to migrate.")

    # --- blogs ---
    print("Fetching blogs.json...")
    blogs = gh_read(GH_FILES["blogs"])
    if isinstance(blogs, list) and blogs:
        ok, err = persistence.save_blogs(blogs)
        print(f"  Migrated {len(blogs)} blog post(s)." if ok else f"  FAILED: {err}")
    else:
        print("  No blog posts found — nothing to migrate.")

    # --- pro requests ---
    print("Fetching pro_requests.json...")
    reqs = gh_read(GH_FILES["requests"])
    if isinstance(reqs, list) and reqs:
        ok, err = persistence.save_requests(reqs)
        print(f"  Migrated {len(reqs)} pro request(s)." if ok else f"  FAILED: {err}")
    else:
        print("  No pro requests found — nothing to migrate.")

    # --- limits config ---
    print("Fetching limits.json...")
    limits = gh_read(GH_FILES["limits"])
    if isinstance(limits, dict) and limits:
        ok, err = persistence.save_limits(limits)
        print(f"  Migrated limits config ({len(limits)} keys)." if ok else f"  FAILED: {err}")
    else:
        print("  No limits config found — the app will use built-in defaults, which is fine.")

    # --- usage tracking ---
    print("Fetching usage_tracking.json...")
    usage = gh_read(GH_FILES["usage"])
    if isinstance(usage, dict) and usage:
        ok, err = persistence.save_usage(usage)
        print(f"  Migrated usage records for {len(usage)} IP hash(es)." if ok else f"  FAILED: {err}")
    else:
        print("  No usage data found — fine, it'll just start fresh.")

    print()
    print("=== Migration complete ===")
    print("Verify before removing GITHUB_TOKEN from .env:")
    print("  python3 -c \"import persistence; print(len(persistence.load_license_keys()), 'keys loaded')\"")


if __name__ == "__main__":
    migrate()
