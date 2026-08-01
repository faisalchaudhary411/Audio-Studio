"""
music_engine.py — real music generation via Replicate's hosted ACE-Step model.

Why this approach instead of self-hosting (same tradeoff as clone_engine.py,
but worse in this case): ACE-Step's own repo needs a git-clone-and-build-from-
source install with a local-path dependency (nano-vllm) and is built around
GPU cloud deployment — it doesn't fit Render's plain `pip install -r
requirements.txt` buildpack at all, unlike Chatterbox which at least installs
as a normal package. Replicate hosts it instead: plain REST calls, no torch,
no model weights, no GPU/RAM to manage on Render. This is architecturally the
same pattern as edge-tts — call an external service, don't run the model here.

Why ACE-Step specifically and not MusicGen: MusicGen's license is CC BY-NC 4.0
(non-commercial only) — same trap as XTTS-v2 earlier in this project. ACE-Step
is Apache 2.0 (both code and weights), genuinely commercial-safe. Verified via
Replicate's own listing before writing this.

COST: this is NOT free like edge-tts. Replicate bills ~$0.02-0.03 per
generation (billed to whatever REPLICATE_API_TOKEN account you set). Gated
Pro-only in app.py for exactly this reason — flip that gate at your own risk
if you want free users generating music on your dime.
"""

import os
import time
import threading
import uuid
import requests

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()
REPLICATE_MODEL = "lucataco/ace-step"  # Apache 2.0 — verified on Replicate's model page

_jobs = {}


def _headers():
    return {"Authorization": f"Bearer {REPLICATE_API_TOKEN}", "Content-Type": "application/json"}


def _run_music_job(job_id: str, tags: str, lyrics: str, duration: int, seed: int = None):
    _jobs[job_id]["status"] = "starting"
    try:
        payload = {
            "input": {
                "tags": tags,
                "lyrics": lyrics or "[inst]",  # "[inst]" = instrumental, no vocals
                "duration": duration,
            }
        }
        if seed is not None:
            payload["input"]["seed"] = seed

        r = requests.post(
            f"https://api.replicate.com/v1/models/{REPLICATE_MODEL}/predictions",
            headers=_headers(), json=payload, timeout=30,
        )
        if r.status_code not in (200, 201):
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = f"Replicate error {r.status_code}: {r.text[:200]}"
            return

        prediction = r.json()
        get_url = prediction["urls"]["get"]
        _jobs[job_id]["status"] = "generating"

        # Poll — typical completion is ~30s per Replicate's own listing.
        for _ in range(90):  # up to ~3 minutes before giving up
            time.sleep(2)
            pr = requests.get(get_url, headers=_headers(), timeout=15)
            data = pr.json()
            status = data.get("status")
            if status == "succeeded":
                output = data.get("output")
                audio_url = output if isinstance(output, str) else (output[0] if output else None)
                if not audio_url:
                    _jobs[job_id]["status"] = "error"
                    _jobs[job_id]["error"] = "Replicate returned no audio output."
                    return
                audio_resp = requests.get(audio_url, timeout=30)
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["audio"] = audio_resp.content
                _jobs[job_id]["audio_url"] = audio_url
                return
            if status == "failed" or status == "canceled":
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = data.get("error") or f"Generation {status}."
                return
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = "Timed out waiting for Replicate (took longer than 3 minutes)."
    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)


def start_music_job(tags: str, lyrics: str = "", duration: int = 60, seed: int = None) -> dict:
    if not REPLICATE_API_TOKEN:
        return {"error": "Music generation isn't configured on this deployment (missing REPLICATE_API_TOKEN)."}
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"status": "queued", "audio": None, "error": None}
    thread = threading.Thread(target=_run_music_job, args=(job_id, tags, lyrics, duration, seed), daemon=True)
    thread.start()
    return {"job_id": job_id}


def get_job(job_id: str):
    return _jobs.get(job_id)
