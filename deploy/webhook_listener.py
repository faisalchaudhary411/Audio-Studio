"""
webhook_listener.py — GitHub push-webhook auto-deploy for VoxCraft.

Matches Render's "push to deploy" convenience, which matters a lot given
Faisal edits exclusively through GitHub's web editor on mobile — no local
git, no manual SSH-and-pull step needed after each edit.

Flow on every push to `main`:
  1. GitHub POSTs to /webhook/voxcraft-deploy with an X-Hub-Signature-256
     header (HMAC-SHA256 of the raw body, using a shared secret).
  2. This listener verifies that signature BEFORE doing anything else —
     an unverified webhook endpoint that runs `git pull` + restarts a
     service is a straightforward remote-code-execution hole (anyone who
     finds the URL could push arbitrary commands via a crafted payload —
     or worse, if verification is skipped, they don't even need a payload,
     just a POST).
  3. On valid signature + push to main: git pull, pip install (in venv),
     systemctl restart voxcraft.

Runs as the unprivileged `deploy` user via systemd — see
voxcraft-webhook.service. It can only run the ONE systemctl command granted
by the sudoers rule (voxcraft-deploy-sudoers), nothing broader.
"""

import hashlib
import hmac
import os
import subprocess
import logging

from flask import Flask, request, abort

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("voxcraft-webhook")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
APP_DIR = os.environ.get("APP_DIR", "/home/deploy/voxcraft")
BRANCH = os.environ.get("DEPLOY_BRANCH", "main")

if not WEBHOOK_SECRET:
    raise RuntimeError(
        "WEBHOOK_SECRET is not set. Refusing to start an unauthenticated "
        "deploy webhook — anyone who finds the URL could trigger deploys."
    )


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """Constant-time comparison of GitHub's HMAC-SHA256 signature against
    one computed locally with the shared secret. Using hmac.compare_digest
    (not ==) avoids leaking timing information about the correct value."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), payload_body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)


@app.route("/webhook/voxcraft-deploy", methods=["POST"])
def deploy_webhook():
    signature = request.headers.get("X-Hub-Signature-256", "")
    raw_body = request.get_data()  # raw bytes — MUST hash the exact bytes GitHub signed

    if not verify_signature(raw_body, signature):
        log.warning("Rejected webhook: invalid or missing signature.")
        abort(403)

    payload = request.get_json(silent=True) or {}
    ref = payload.get("ref", "")

    if ref != f"refs/heads/{BRANCH}":
        log.info("Ignoring push to %s (only deploying on %s).", ref, BRANCH)
        return {"status": "ignored", "reason": f"not a push to {BRANCH}"}, 200

    log.info("Valid push to %s — starting deploy.", BRANCH)
    try:
        _run_deploy()
    except subprocess.CalledProcessError as e:
        log.error("Deploy step failed: %s\nSTDOUT: %s\nSTDERR: %s", e, e.stdout, e.stderr)
        return {"status": "error", "detail": str(e)}, 500
    except OSError as e:
        log.error("Deploy step failed: %s", e)
        return {"status": "error", "detail": str(e)}, 500

    log.info("Deploy complete.")
    return {"status": "deployed"}, 200


def _run_deploy():
    # git pull
    subprocess.run(
        ["git", "pull", "origin", BRANCH],
        cwd=APP_DIR, check=True, capture_output=True, text=True,
    )
    # reinstall deps in case requirements.txt changed
    pip_path = os.path.join(APP_DIR, "venv", "bin", "pip")
    subprocess.run(
        [pip_path, "install", "-r", os.path.join(APP_DIR, "requirements.txt")],
        cwd=APP_DIR, check=True, capture_output=True, text=True,
    )
    # restart the app — this exact command is the ONLY thing the sudoers
    # rule allows the deploy user to run passwordless (see
    # voxcraft-deploy-sudoers). Nothing broader is granted.
    subprocess.run(
        ["sudo", "/usr/bin/systemctl", "restart", "voxcraft"],
        check=True, capture_output=True, text=True,
    )


@app.route("/webhook/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("WEBHOOK_PORT", 9001))
    # Bound to 127.0.0.1 only — never exposed directly to the internet.
    # Nginx proxies /webhook/voxcraft-deploy to this port (see nginx config).
    app.run(host="127.0.0.1", port=port, debug=False)
