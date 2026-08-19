"""
modal_client.py — thin client for the Chatterbox voice-clone worker running
on Modal (see modal_workers/chatterbox/app.py).

Simpler than the RunPod client this replaced: Modal's endpoint is a normal
synchronous HTTP POST, not an async job queue. clone_engine.py already
calls this from a background thread (decoupled from the actual Flask
request/response cycle — see that file's docstring), so one blocking call
here for up to a few minutes is fine.

Requires MODAL_CLONE_ENDPOINT_URL set on the VPS — the URL Modal prints
after `modal deploy` (also visible in the GitHub Actions deploy log), e.g.
https://<workspace>--voxcraft-clone-worker-chatterboxworker-generate.modal.run
"""

import os
import requests

MODAL_CLONE_ENDPOINT_URL = os.environ.get("MODAL_CLONE_ENDPOINT_URL", "").strip()

# Generous — covers a cold start (container spin-up + model load, can be
# 20-60s on top of generation time) plus actual generation.
#
# BUG FIX: was 240s. A max-length request (CLONE_CHAR_LIMIT=2000 chars on
# the VPS) splits into ~10 chunks server-side (MAX_CHUNK_CHARS=200 in
# modal_workers/chatterbox/app.py), and real production timing showed
# ~25s/chunk — ~250s just for generation on a long request, before cold
# start. Worse, the worker's OWN timeout used to be 300s, meaning this
# client could give up and report a false timeout while the GPU container
# kept running (and billing) toward its own later cutoff. Raised to 650s,
# safely above the worker's now-600s timeout (see that file), so this
# client never gives up before the worker's own hard limit would.
_TIMEOUT_SEC = 650


def is_configured() -> bool:
    return bool(MODAL_CLONE_ENDPOINT_URL)


def generate(text: str, reference_audio_b64: str, language_id: str = "en") -> dict:
    """Blocking call. Returns {"success": True, "audio_b64": ...} or
    {"success": False, "error": ...}. language_id: "en" or "hi" (see
    urdu_transliteration.py for how Urdu maps to "hi")."""
    if not MODAL_CLONE_ENDPOINT_URL:
        return {"success": False, "error": "Voice cloning isn't configured on this deployment yet "
                                             "— set MODAL_CLONE_ENDPOINT_URL."}
    try:
        r = requests.post(
            MODAL_CLONE_ENDPOINT_URL,
            json={"text": text, "reference_audio_b64": reference_audio_b64, "language_id": language_id},
            timeout=_TIMEOUT_SEC,
        )
        if r.status_code != 200:
            return {"success": False, "error": f"Worker returned HTTP {r.status_code}."}
        data = r.json()
        if data.get("error"):
            return {"success": False, "error": data["error"]}
        if not data.get("audio_b64"):
            return {"success": False, "error": "Worker returned no audio."}
        return {"success": True, "audio_b64": data["audio_b64"]}
    except requests.exceptions.Timeout:
        return {"success": False, "error": f"Timed out after {_TIMEOUT_SEC}s waiting for the GPU worker."}
    except Exception as e:
        return {"success": False, "error": str(e)}
