"""
modal_clone.py — VoxCraft client for Chatterbox Multilingual voice cloning on Modal.

Talks to the single-chunk GPU endpoint deployed from
modal_workers/chatterbox/app.py (ChatterboxWorker.generate), which expects
{chunk_text, reference_audio_b64, language_id, already_processed} and
returns {success, audio_b64, error}.

clone_engine.py already splits long text into short segments itself
(_split_for_stable_generation, <=280 chars) and calls modal_client.generate()
once per segment, so this client only ever needs to send one chunk at a
time — no parallel/multi-chunk handling needed here (contrast with
modal_f5tts.py, which does its own internal chunk-splitting for long-script
mode).

FIXES APPLIED (see clone-quality investigation):
1. Added retry-with-backoff, mirroring modal_f5tts.py's
   _process_f5tts_chunk_with_retry. Previously a single timed-out/failed
   segment aborted the ENTIRE job — clone_engine.py's executor.map bails on
   the first non-success result, discarding every other segment that had
   already generated successfully. On a 6000-char script split into ~20
   segments, that's ~20 independent chances for one flaky request to waste
   the whole job. Retrying in-place (same segment, fresh request) fixes the
   large majority of these without touching clone_engine.py's job logic.
2. Added `already_processed` passthrough — lets clone_engine.py preprocess
   the reference clip ONCE per job (see _run_clone_job) instead of the
   worker re-running ffmpeg denoise/silence-trim/loudnorm on every single
   segment call with byte-identical input.

Requires this env var set on the VPS:
  MODAL_CLONE_ENDPOINT_URL — the deployed Modal endpoint URL for
                             ChatterboxWorker.generate
"""

import os
import time
import logging
import requests

CLONE_ENDPOINT_URL = os.environ.get("MODAL_CLONE_ENDPOINT_URL", "").strip()

# Matches the Modal worker's own timeout (600s, see
# modal_workers/chatterbox/app.py's @app.cls(timeout=600)) plus headroom for
# cold starts, same margin modal_f5tts.py uses.
_TIMEOUT_SEC = 650

# Same retry count as modal_f5tts.py, for consistency between the two engines.
MAX_RETRIES = 2

logger = logging.getLogger(__name__)

# Reuse connections across requests for lower latency (matches modal_f5tts.py).
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})


def is_configured() -> bool:
    return bool(CLONE_ENDPOINT_URL)


def _generate_audio_once(text: str, reference_audio_b64: str, language_id: str,
                          already_processed: bool) -> dict:
    """Single attempt — no retry here, generate_audio()'s wrapper handles that."""
    payload = {
        "chunk_text": text,
        "reference_audio_b64": reference_audio_b64,
        "language_id": language_id if language_id in ("en", "hi") else "en",
        "already_processed": already_processed,
    }

    try:
        r = _session.post(CLONE_ENDPOINT_URL, json=payload, timeout=_TIMEOUT_SEC)
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


def generate_audio(text: str, reference_audio_b64: str, language_id: str = "en",
                    already_processed: bool = False) -> dict:
    """
    Sends a single text chunk + reference voice to the Chatterbox Modal
    endpoint, retrying transient failures with exponential backoff before
    giving up. Returns {"success": True, "audio_b64": ...} or
    {"success": False, "error": ...} — same shape clone_engine.py expects
    from modal_client.generate().
    """
    if not CLONE_ENDPOINT_URL:
        return {"success": False, "error": "Clone Endpoint URL is not configured."}

    last_result = None
    for attempt in range(MAX_RETRIES + 1):
        result = _generate_audio_once(text, reference_audio_b64, language_id, already_processed)
        if result.get("success"):
            return result
        last_result = result
        if attempt < MAX_RETRIES:
            wait = 2 ** attempt  # 1s, then 2s
            logger.warning(
                "Chatterbox segment attempt %d failed, retrying in %ds: %s",
                attempt + 1, wait, result.get("error"),
            )
            time.sleep(wait)
        else:
            logger.error(
                "Chatterbox segment exhausted all %d attempts: %s",
                MAX_RETRIES + 1, result.get("error"),
            )

    return last_result
