"""
clone_engine.py — voice cloning via Chatterbox-Turbo (Resemble AI, MIT
license — genuinely free for commercial use, unlike XTTS-v2/F5-TTS whose
official weights are CC-BY-NC-4.0, non-commercial only).

Runs on Modal (modal_workers/chatterbox/app.py), not on this VPS — a clone
request could otherwise pin the CPU for 10-60+ seconds or exhaust RAM on a
1 vCPU / 2GB VPS shared with the rest of the site.

CHANGED (again): originally used RunPod (async /run + /status polling).
Switched to Modal because RunPod's minimum account deposit turned out to
be a real barrier, and Modal offers $30/month free compute credit with no
deposit at all. Modal's endpoint is a plain synchronous HTTP call rather
than a job queue, so this file is simpler than the RunPod version was —
no polling loop, just one blocking request from the background thread.
Same public interface (start_clone_job / get_job) either way, so app.py's
routes never needed to change across either swap.
"""

import base64
import threading
import uuid

import modal_client

_jobs = {}


def _run_clone_job(job_id: str, text: str, reference_audio_path: str):
    _jobs[job_id]["status"] = "generating"
    try:
        with open(reference_audio_path, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode("ascii")

        result = modal_client.generate(text, ref_b64)
        if not result.get("success"):
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = result.get("error", "Generation failed.")
            return

        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["audio"] = base64.b64decode(result["audio_b64"])
    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)


def start_clone_job(text: str, reference_audio_path: str) -> str:
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"status": "queued", "audio": None, "error": None}
    if not modal_client.is_configured():
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = ("Voice cloning isn't configured on this deployment yet — "
                                   "set MODAL_CLONE_ENDPOINT_URL.")
        return job_id
    thread = threading.Thread(target=_run_clone_job, args=(job_id, text, reference_audio_path), daemon=True)
    thread.start()
    return job_id


def get_job(job_id: str):
    return _jobs.get(job_id)
