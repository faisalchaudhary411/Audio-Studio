"""
clone_engine.py — voice cloning via Chatterbox-Turbo (Resemble AI, MIT
license — genuinely free for commercial use, unlike XTTS-v2/F5-TTS whose
official weights are CC-BY-NC-4.0, non-commercial only).

CHANGED: this used to run Chatterbox-Turbo locally, in-process, on CPU —
viable in theory but risky in practice on a 1 vCPU / 2GB RAM VPS shared
with the rest of the site: a single clone request could pin the CPU for
10-60+ seconds and degrade every other visitor's TTS requests at the same
time, or exhaust the VPS's RAM entirely (Chatterbox + torch is a heavy
process to load alongside gunicorn + librosa + everything else already
running). Now it submits the job to a RunPod serverless GPU endpoint
instead — same public interface (start_clone_job / get_job) so app.py's
routes didn't need to change, but the actual model never touches this VPS.

Deploy the worker in runpod_workers/chatterbox/ to RunPod, then set
RUNPOD_API_KEY and RUNPOD_CLONE_ENDPOINT_ID to that endpoint's ID.
"""

import base64
import threading
import time
import uuid

import runpod_client

# In-memory job store. Fine for a single VPS instance; if you ever scale to
# multiple instances behind a load balancer you'll need a shared store
# (Redis) instead of this dict, same caveat as music_engine.py already has.
_jobs = {}

_POLL_INTERVAL_SEC = 2
_POLL_TIMEOUT_SEC = 180  # RunPod cold starts can take 30-60s+ on top of generation time


def _run_clone_job(job_id: str, text: str, reference_audio_path: str):
    _jobs[job_id]["status"] = "submitting"
    try:
        with open(reference_audio_path, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode("ascii")

        submit = runpod_client.submit_job("clone", {"text": text, "reference_audio_b64": ref_b64})
        if not submit.get("success"):
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = submit.get("error", "Failed to submit the cloning job.")
            return

        runpod_job_id = submit["job_id"]
        _jobs[job_id]["status"] = "generating"

        deadline = time.time() + _POLL_TIMEOUT_SEC
        while time.time() < deadline:
            time.sleep(_POLL_INTERVAL_SEC)
            status = runpod_client.get_job_status("clone", runpod_job_id)
            state = status.get("status")

            if state == "COMPLETED":
                output = status.get("output") or {}
                audio_b64 = output.get("audio_b64")
                if not audio_b64:
                    _jobs[job_id]["status"] = "error"
                    _jobs[job_id]["error"] = "The worker finished but returned no audio."
                    return
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["audio"] = base64.b64decode(audio_b64)
                return

            if state in ("FAILED", "CANCELLED", "ERROR"):
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = status.get("error") or f"Generation {state.lower()}."
                return
            # IN_QUEUE / IN_PROGRESS — keep polling

        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = f"Timed out waiting for the GPU worker (over {_POLL_TIMEOUT_SEC}s)."
    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)


def start_clone_job(text: str, reference_audio_path: str) -> str:
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"status": "queued", "audio": None, "error": None}
    if not runpod_client.is_configured("clone"):
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = ("Voice cloning isn't configured on this deployment yet — "
                                   "set RUNPOD_API_KEY and RUNPOD_CLONE_ENDPOINT_ID.")
        return job_id
    thread = threading.Thread(target=_run_clone_job, args=(job_id, text, reference_audio_path), daemon=True)
    thread.start()
    return job_id


def get_job(job_id: str):
    return _jobs.get(job_id)
