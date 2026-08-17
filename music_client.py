"""
music_client.py — thin client for the self-hosted ACE-Step 1.5 music worker
running on Modal (see modal_workers/ace_step/app.py).

Same pattern as modal_client.py (voice cloning): a synchronous HTTP POST,
not an async job queue — Modal's endpoint just blocks until the audio is
generated. music_engine.py already calls this from a background thread (see
that file's docstring), so one blocking call here for up to a few minutes
is fine.

Requires MODAL_MUSIC_ENDPOINT_URL set on the VPS — the URL Modal prints
after `modal deploy` (also visible in the GitHub Actions deploy log), e.g.
https://<workspace>--voxcraft-music-worker-acestepworker-generate.modal.run
"""

import os
import requests

MODAL_MUSIC_ENDPOINT_URL = os.environ.get("MODAL_MUSIC_ENDPOINT_URL", "").strip()

# Generous — a warm container is fast (ACE-Step 1.5 turbo generates in
# seconds), but a cold start has to load two models (DiT + LM) and, on a
# from-scratch container, may still be finishing a multi-GB weight download
# into the Modal Volume the very first time. Subsequent calls to an
# already-warm container are much faster than this ceiling.
_TIMEOUT_SEC = 420


def is_configured() -> bool:
    return bool(MODAL_MUSIC_ENDPOINT_URL)


def generate(prompt: str, lyrics: str = "", duration: float = 60.0,
             seed: int = None, audio_format: str = "wav") -> dict:
    """Blocking call. Returns {"success": True, "audio_b64": ..., "audio_format": ...}
    or {"success": False, "error": ...}."""
    if not MODAL_MUSIC_ENDPOINT_URL:
        return {
            "success": False,
            "error": "Music generation isn't configured on this deployment yet "
                     "— set MODAL_MUSIC_ENDPOINT_URL.",
        }
    try:
        r = requests.post(
            MODAL_MUSIC_ENDPOINT_URL,
            json={
                "prompt": prompt,
                "lyrics": lyrics,
                "duration": duration,
                "seed": seed,
                "audio_format": audio_format,
            },
            timeout=_TIMEOUT_SEC,
        )
        if r.status_code != 200:
            return {"success": False, "error": f"Worker returned HTTP {r.status_code}."}
        data = r.json()
        if data.get("error"):
            return {"success": False, "error": data["error"]}
        if not data.get("audio_b64"):
            return {"success": False, "error": "Worker returned no audio."}
        return {
            "success": True,
            "audio_b64": data["audio_b64"],
            "audio_format": audio_format,
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": f"Timed out after {_TIMEOUT_SEC}s waiting for the GPU worker."}
    except Exception as e:
        return {"success": False, "error": str(e)}
