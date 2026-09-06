"""
modal_whisper.py — VoxCraft client for the faster-whisper Modal GPU worker.

Talks to WhisperWorker.transcribe deployed from
modal_workers/whisper/app.py.

Requires on the VPS:
  MODAL_WHISPER_ENDPOINT_URL — full HTTPS endpoint URL for the
                               WhisperWorker.transcribe fastapi endpoint

Usage from audio_tools / app:
  from modal_whisper import is_configured, transcribe_audio
  if is_configured():
      result = transcribe_audio(file_bytes, language="hi", ...)
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Optional

import requests

# Read env on every check (not only at import) so a service restart that
# loads .env is enough — no need to re-import the module.
def _endpoint_url() -> str:
    return (os.environ.get("MODAL_WHISPER_ENDPOINT_URL") or "").strip()


# Worker timeout is 600s; allow headroom for cold start + long files.
_TIMEOUT_SEC = 650
MAX_RETRIES = 2

logger = logging.getLogger(__name__)

_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})


def is_configured() -> bool:
    return bool(_endpoint_url())


def _transcribe_once(
    audio_bytes: bytes,
    language: Optional[str] = None,
    task: str = "transcribe",
    model_size: str = "large-v3",
    word_timestamps: bool = False,
    vad_filter: bool = True,
    initial_prompt: Optional[str] = None,
    endpoint_url: Optional[str] = None,
) -> dict:
    url = (endpoint_url or _endpoint_url()).strip()
    payload = {
        "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
        "language": language,
        "task": task,
        "model_size": model_size,
        "word_timestamps": word_timestamps,
        "vad_filter": vad_filter,
        "initial_prompt": initial_prompt,
    }

    try:
        r = _session.post(url, json=payload, timeout=_TIMEOUT_SEC)
        if r.status_code == 200:
            res = r.json()
            if res.get("success") and (res.get("text") is not None):
                return {
                    "success": True,
                    "text": res.get("text") or "",
                    "language": res.get("language") or "",
                    "language_probability": res.get("language_probability", 0.0),
                    "duration_sec": res.get("duration_sec", 0.0),
                    "segments": res.get("segments") or [],
                    "srt": res.get("srt") or "",
                    "method": res.get("method") or "faster-whisper",
                    "provider": "whisper_modal",
                }
            return {
                "success": False,
                "error": res.get("error") or "Empty transcription from Whisper worker.",
            }
        return {
            "success": False,
            "error": f"Modal Whisper worker returned HTTP {r.status_code}.",
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timed out reaching the Modal Whisper worker."}
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "error": f"Modal Whisper worker unreachable (network/DNS): {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error calling Modal Whisper worker: {e}",
        }


def transcribe_audio(
    audio_bytes: bytes,
    language: Optional[str] = None,
    task: str = "transcribe",
    model_size: str = "large-v3",
    word_timestamps: bool = False,
    vad_filter: bool = True,
    initial_prompt: Optional[str] = None,
) -> dict:
    """
    Transcribe (or translate) audio bytes via the Modal faster-whisper worker.

    Returns a dict shaped for audio_tools / the Transcribe tool:
      success, text, method, language, duration_sec, srt, segments, ...
    or {success: False, error: "..."}.
    """
    endpoint = _endpoint_url()
    if not endpoint:
        return {
            "success": False,
            "error": "Whisper Endpoint URL is not configured (MODAL_WHISPER_ENDPOINT_URL).",
        }

    if not audio_bytes:
        return {"success": False, "error": "Empty audio payload."}

    # Normalize language: accept "en-US" / "hi-IN" → "en" / "hi"
    lang = None
    if language:
        lang = str(language).strip().lower().split("-")[0] or None
        if lang in ("", "auto", "none"):
            lang = None

    last_result = None
    for attempt in range(MAX_RETRIES + 1):
        last_result = _transcribe_once(
            audio_bytes,
            language=lang,
            task=task,
            model_size=model_size,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter,
            initial_prompt=initial_prompt,
            endpoint_url=endpoint,
        )
        if last_result.get("success"):
            return last_result
        if attempt < MAX_RETRIES:
            wait = 1.5 * (2 ** attempt)
            logger.warning(
                "Whisper attempt %s failed: %s — retrying in %.1fs",
                attempt + 1,
                last_result.get("error"),
                wait,
            )
            time.sleep(wait)

    logger.error("Whisper worker failed after retries: %s", (last_result or {}).get("error"))
    return last_result or {"success": False, "error": "Whisper worker failed."}
