"""
Push admin-edited page content overrides (the page_content SQLite table,
edited via /admin/seo) into a JSON file committed directly to GitHub, via
the Contents API — no local git checkout/push involved.

Why this exists: /admin/seo edits are DB-only and take effect instantly
(see persistence.py's page_content functions). That's great for speed, but
it means the DB and the code defaults in tool_pages.py/seo_pages.py can
drift apart, and if the DB were ever lost (fresh VPS, botched migration,
restore from an old backup) those edits would silently revert to whatever
was last hardcoded in the .py files.

This module is the other half of that fix:
  - Faisal reviews/finishes a batch of edits in /admin/seo
  - clicks "Push all changes to repo" (manual, batched — not per-save, so
    a run of edits doesn't spam commits or fight with the auto-deploy
    webhook mid-edit)
  - this writes the *current full* page_content table as one JSON file at
    data/page_content_overrides.json in the repo
  - tool_pages.py/seo_pages.py load that JSON at import time and merge it
    under their hardcoded dicts (see the loader added at the bottom of
    tool_pages.py), so a fresh deploy — even with a brand new, empty DB —
    already reflects the last-synced admin content instead of stale
    hardcoded copy

Deliberately does NOT rewrite tool_pages.py/seo_pages.py's Python source
directly — regenerating hand-written dict literals programmatically is a
"one bug corrupts the whole file" risk for very little benefit over a
plain JSON data file the code merges in.

REQUIRED ENV VARS:
- GITHUB_TOKEN — a PAT (classic 'repo' scope, or fine-grained with
  Contents: read+write) on this one repo. Not the same GITHUB_TOKEN
  mentioned as "no longer needed" elsewhere in this codebase — that was
  about the old GitHub-JSON persistence layer, since removed. This is a
  new, narrower-purpose use of the same env var name; if you already have
  a token from that era, its scope should still work here.
- GITHUB_REPO — "owner/repo-name"

OPTIONAL ENV VARS:
- GITHUB_BRANCH — defaults to "main". Push targets this branch, and if
  your GitHub Actions deploy workflow watches this branch, a sync commit
  will trigger a normal redeploy — same as any other push. Point this at
  a non-deploy branch if you'd rather review via PR before it goes live.
- GITHUB_OVERRIDES_PATH — defaults to "data/page_content_overrides.json"
"""

import base64
import json
import os
import urllib.error
import urllib.request

GITHUB_API = "https://api.github.com"
DEFAULT_OVERRIDES_PATH = "data/page_content_overrides.json"


def _gh_request(method: str, url: str, token: str, body: dict = None):
    """Minimal GitHub REST call — stdlib only, no new dependency for one
    call site. Returns (status_code, parsed_json_dict)."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "voxcraft-admin-sync")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            parsed = {"message": raw}
        return e.code, parsed
    except urllib.error.URLError as e:
        return 0, {"message": str(e.reason)}


def push_overrides_to_repo(overrides: dict) -> tuple:
    """Commit the full current page_content overrides dict to
    GITHUB_OVERRIDES_PATH on GITHUB_REPO@GITHUB_BRANCH. Creates the file
    on first-ever sync, updates it on every sync after. Returns (ok, msg)
    — never raises, so a bad token or network hiccup surfaces as a normal
    admin-panel error message instead of a 500."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPO", "").strip()
    branch = os.environ.get("GITHUB_BRANCH", "main").strip()
    path = os.environ.get("GITHUB_OVERRIDES_PATH", DEFAULT_OVERRIDES_PATH).strip()

    if not token or not repo:
        return False, ("GITHUB_TOKEN and/or GITHUB_REPO env var not set — "
                        "see github_sync.py's docstring for what's needed.")

    content_str = json.dumps(overrides, ensure_ascii=False, indent=2) + "\n"
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("ascii")
    base_url = f"{GITHUB_API}/repos/{repo}/contents/{path}"

    # Fetch the existing file's sha (required by the Contents API to
    # update a file rather than create one). Absent entirely on the very
    # first sync, when the file doesn't exist in the repo yet — that's
    # expected, not an error.
    status, existing = _gh_request("GET", f"{base_url}?ref={branch}", token)
    sha = existing.get("sha") if status == 200 else None

    page_count = len(overrides)
    payload = {
        "message": f"Sync {page_count} page content override{'s' if page_count != 1 else ''} (admin)",
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    status, result = _gh_request("PUT", base_url, token, payload)
    if status in (200, 201):
        commit_sha = ((result.get("commit") or {}).get("sha") or "")[:7]
        return True, f"Pushed {page_count} page override{'s' if page_count != 1 else ''} to {repo}@{branch} ({commit_sha})."
    return False, f"GitHub API error ({status}): {result.get('message', 'unknown error')}"
