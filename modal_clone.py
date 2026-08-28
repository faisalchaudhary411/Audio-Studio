"""
modal_clone.py — VoxCraft client for Chatterbox Multilingual voice cloning on Modal.

Talks to the single-chunk GPU endpoint deployed from
modal_workers/chatterbox/app.py (ChatterboxWorker.generate), which expects
{chunk_text, reference_audio_b64, language_id} and returns
{success, audio_b64, error}.

clone_engine.py already splits long text into short segments itself
(_split_for_stable_generation, <=380 chars) and calls modal_client.generate()
once per segment, so this client only ever needs to send one chunk at a
time — no parallel/multi-chunk handling needed here (contrast with
modal_f5tts.py, which does its own internal chunk-splitting for long-script
mode).

Requires this env var set on the VPS:
  MODAL_CLONE_ENDPOINT_URL — the deployed Modal endpoint URL for
                             ChatterboxWorker.generate
"""

import os
import requests

CLONE_ENDPOINT_URL = os.environ.get("MODAL_CLONE_ENDPOINT_URL", "").strip()

# Matches the Modal worker's own timeout (600s, see
# modal_workers/chatterbox/app.py's @app.cls(timeout=600)) plus headroom for
# cold starts, same margin modal_f5tts.py uses.
_TIMEOUT_SEC = 650


def is_configured() -> bool:
    return bool(CLONE_ENDPOINT_URL)


def generate_audio(text: str, reference_audio_b64: str, language_id: str = "en") -> dict:
    """
    Sends a single text chunk + reference voice to the Chatterbox Modal
    endpoint. Returns {"success": True, "audio_b64": ...} or
    {"success": False, "error": ...} — same shape clone_engine.py expects
    from modal_client.generate().
    """
    if not CLONE_ENDPOINT_URL:
        return {"success": False, "error": "Clone Endpoint URL is not configured."}

    payload = {
        "chunk_text": text,
        "reference_audio_b64": reference_audio_b64,
        "language_id": language_id if language_id in ("en", "hi") else "en",
    }

    try:
        r = requests.post(CLONE_ENDPOINT_URL, json=payload, timeout=_TIMEOUT_SEC)
        if r.status_code == 200:
            res = r.json()
            if res.get("success") and res.get("audio_b64"):
                return {"success": True, "audio_b64": res["audio_b64"], "provider": "chatterbox_modal"}
            return {"success": False, "error": res.get("error", "Empty output from clone worker.")}
        return {"success": False, "error": f"Modal clone worker returned HTTP {r.status_code}."}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timed out reaching the Modal clone worker."}
    except requests.exceptions.ConnectionError as e:
        return {"success": False, "error": f"Modal clone worker unreachable (network/DNS issue): {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error calling Modal clone worker: {e}"}
