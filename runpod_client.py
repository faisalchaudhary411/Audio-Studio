"""
runpod_client.py — thin wrapper around RunPod's serverless REST API.

GPU jobs (voice cloning) take 20-90+ seconds, which is far too long to
hold open inside a gunicorn worker on a 2GB VPS with only 2 workers — one
slow request would starve every other visitor on the site for its whole
duration. So this always uses RunPod's ASYNC endpoint (/run, not /runsync):
submit the job, get a job_id back immediately. clone_engine.py runs a
background thread that polls this client's get_job_status() and stores the
final result in its own in-memory job store — the same pattern
music_engine.py already used for polling Replicate. The browser then polls
app.py's /api/clone/status/<job_id> (that in-memory store), never RunPod
directly.

Requires a RunPod serverless endpoint already deployed running the
Chatterbox-Turbo worker (see runpod_workers/chatterbox/ in this repo for
the Docker image to deploy), and these env vars set on the VPS:
  RUNPOD_API_KEY            — from RunPod dashboard → Settings → API Keys
  RUNPOD_CLONE_ENDPOINT_ID  — that endpoint's ID
"""

import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "").strip()
RUNPOD_CLONE_ENDPOINT_ID = os.environ.get("RUNPOD_CLONE_ENDPOINT_ID", "").strip()

_BASE = "https://api.runpod.ai/v2"

# Registry so app.py's poll route can look up an endpoint ID by a short
# name in the URL (e.g. /api/job-status/clone/<job_id>) instead of trusting
# a raw endpoint ID from the client — the client should never get to choose
# which RunPod endpoint gets hit.
ENDPOINTS = {
    "clone": RUNPOD_CLONE_ENDPOINT_ID,  # runs Chatterbox-Turbo, see runpod_workers/chatterbox/
}


def is_configured(name: str) -> bool:
    return bool(RUNPOD_API_KEY and ENDPOINTS.get(name))


def submit_job(name: str, payload: dict) -> dict:
    """Submits an async job. Returns {"success": True, "job_id": ...} or
    {"success": False, "error": ...}."""
    endpoint_id = ENDPOINTS.get(name)
    if not (RUNPOD_API_KEY and endpoint_id):
        return {"success": False, "error": f"RunPod isn't configured for '{name}' on this deployment yet."}
    try:
        r = requests.post(
            f"{_BASE}/{endpoint_id}/run",
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"},
            json={"input": payload},
            timeout=20,
        )
        if r.status_code not in (200, 201):
            return {"success": False, "error": f"RunPod returned HTTP {r.status_code}."}
        data = r.json()
        job_id = data.get("id")
        if not job_id:
            return {"success": False, "error": "RunPod accepted the request but returned no job ID."}
        return {"success": True, "job_id": job_id}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timed out reaching RunPod."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_job_status(name: str, job_id: str) -> dict:
    """Returns RunPod's raw status payload, normalized to always include a
    'status' key: 'IN_QUEUE' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' |
    'CANCELLED' | 'ERROR' (ERROR = our own client-side failure, not a
    RunPod status value, used when the request to RunPod itself fails)."""
    endpoint_id = ENDPOINTS.get(name)
    if not (RUNPOD_API_KEY and endpoint_id):
        return {"status": "ERROR", "error": f"RunPod isn't configured for '{name}'."}
    try:
        r = requests.get(
            f"{_BASE}/{endpoint_id}/status/{job_id}",
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            timeout=15,
        )
        if r.status_code != 200:
            return {"status": "ERROR", "error": f"RunPod returned HTTP {r.status_code}."}
        return r.json()
    except requests.exceptions.Timeout:
        return {"status": "ERROR", "error": "Timed out reaching RunPod."}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
