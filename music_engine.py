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

# BUG FIX: Don't read the token at import time — read it at call time.
# Gunicorn workers import this module once at startup. If the env var
# wasn't set then (e.g. systemd hadn't loaded it yet, or the .env file
# wasn't sourced), the token stays empty forever. Reading at call time
# means a gunicorn graceful reload (SIGHUP) or even just a new request
# will pick up the current env var value.
#
# Also added: explicit .env file fallback, and a diagnostic endpoint
# so you can verify the token is actually visible to the worker process.

REPLICATE_MODEL = "lucataco/ace-step"  # Apache 2.0 — verified on Replicate's model page


def _get_token():
    """Read REPLICATE_API_TOKEN from environment at call time.

    Tries in order:
    1. os.environ (set via export, systemd, docker -e, etc.)
    2. .env file in project root (common for local dev)
    3. .env file in current working directory

    Returns the token string, or "" if not found anywhere.
    """
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if token and token.strip():
        return token.strip()

    # Fallback: try reading from .env file
    for env_path in ["/app/.env", "/opt/voxcraft/.env", os.path.join(os.getcwd(), ".env")]:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("REPLICATE_API_TOKEN="):
                            token = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if token:
                                return token
            except Exception:
                pass

    return ""


def _headers():
    token = _get_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── SQLite job store (same pattern as clone_engine.py) ─────────────────────
# The old in-memory _jobs dict had the same "Unknown job" bug under gunicorn
# that clone_engine had. Fixed here too for consistency.

import sqlite3

JOB_DB_PATH = os.environ.get("MUSIC_JOB_DB_PATH", "/tmp/voxcraft_music_jobs.db")
JOB_MAX_AGE_SECONDS = 600
_db_lock = threading.Lock()


def _db_conn():
    conn = sqlite3.connect(JOB_DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _db_lock:
        conn = _db_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS music_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'queued',
                audio BLOB,
                audio_url TEXT,
                error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_music_jobs_created ON music_jobs(created_at)")
        conn.commit()
        conn.close()


_init_db()

_sweep_thread = None


def _start_sweep_thread():
    global _sweep_thread
    if _sweep_thread is not None and _sweep_thread.is_alive():
        return

    def _sweep_loop():
        while True:
            time.sleep(60)
            try:
                cutoff = time.time() - JOB_MAX_AGE_SECONDS
                with _db_lock:
                    conn = _db_conn()
                    conn.execute("DELETE FROM music_jobs WHERE created_at < ?", (cutoff,))
                    conn.commit()
                    conn.close()
            except Exception:
                pass

    _sweep_thread = threading.Thread(target=_sweep_loop, daemon=True)
    _sweep_thread.start()


_start_sweep_thread()


def _insert_job(job_id: str) -> None:
    now = time.time()
    with _db_lock:
        conn = _db_conn()
        conn.execute(
            "INSERT INTO music_jobs (job_id, status, created_at, updated_at) VALUES (?, 'queued', ?, ?)",
            (job_id, now, now),
        )
        conn.commit()
        conn.close()


def _update_job(job_id: str, status: str = None, audio: bytes = None, audio_url: str = None, error: str = None) -> None:
    fields = []
    values = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if audio is not None:
        fields.append("audio = ?")
        values.append(audio)
    if audio_url is not None:
        fields.append("audio_url = ?")
        values.append(audio_url)
    if error is not None:
        fields.append("error = ?")
        values.append(error)
    if not fields:
        return
    fields.append("updated_at = ?")
    values.append(time.time())
    values.append(job_id)
    with _db_lock:
        conn = _db_conn()
        conn.execute("UPDATE music_jobs SET " + ", ".join(fields) + " WHERE job_id = ?", values)
        conn.commit()
        conn.close()


def _fetch_job(job_id: str):
    conn = _db_conn()
    row = conn.execute(
        "SELECT job_id, status, audio, audio_url, error, created_at, updated_at FROM music_jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "job_id": row["job_id"],
        "status": row["status"],
        "audio": row["audio"],
        "audio_url": row["audio_url"],
        "error": row["error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ── Core music logic ───────────────────────────────────────────────────────

def _run_music_job(job_id: str, tags: str, lyrics: str, duration: int, seed: int = None):
    _update_job(job_id, status="starting")
    try:
        token = _get_token()
        if not token:
            _update_job(
                job_id,
                status="error",
                error=(
                    "REPLICATE_API_TOKEN is not set. "
                    "Check: echo $REPLICATE_API_TOKEN | systemd show-environment | your .env file. "
                    "If you just added it, run: systemctl restart voxcraft (or your service name)."
                ),
            )
            return

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
            _update_job(
                job_id,
                status="error",
                error=f"Replicate error {r.status_code}: {r.text[:500]}",
            )
            return

        prediction = r.json()
        get_url = prediction["urls"]["get"]
        _update_job(job_id, status="generating")

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
                    _update_job(job_id, status="error", error="Replicate returned no audio output.")
                    return
                audio_resp = requests.get(audio_url, timeout=30)
                _update_job(
                    job_id,
                    status="done",
                    audio=audio_resp.content,
                    audio_url=audio_url,
                )
                return
            if status in ("failed", "canceled"):
                _update_job(
                    job_id,
                    status="error",
                    error=data.get("error") or f"Generation {status}.",
                )
                return
        _update_job(
            job_id,
            status="error",
            error="Timed out waiting for Replicate (took longer than 3 minutes).",
        )
    except Exception as e:
        import traceback
        _update_job(job_id, status="error", error=f"{e}\n{traceback.format_exc()}")


# ── Public API ─────────────────────────────────────────────────────────────

def start_music_job(tags: str, lyrics: str = "", duration: int = 60, seed: int = None) -> dict:
    """Queue a music generation job and return its ID immediately."""
    job_id = uuid.uuid4().hex
    _insert_job(job_id)

    # BUG FIX: Check token at call time, not import time. This means if you
    # set the env var after gunicorn started, a graceful reload (SIGHUP) or
    # even just a new request will pick it up — instead of the old behavior
    # where the empty token was cached forever from import time.
    token = _get_token()
    if not token:
        _update_job(
            job_id,
            status="error",
            error=(
                "REPLICATE_API_TOKEN is not set in the environment. "
                "If you just added it, make sure it's exported (export REPLICATE_API_TOKEN=...) "
                "and restart the gunicorn service (not just the VPS). "
                "For systemd: sudo systemctl restart voxcraft. "
                "For supervisor: sudo supervisorctl restart voxcraft."
            ),
        )
        return {"job_id": job_id}  # Return job_id so frontend can poll the detailed error

    thread = threading.Thread(
        target=_run_music_job,
        args=(job_id, tags, lyrics, duration, seed),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


def get_job(job_id: str):
    """Return job dict (or None) — same shape as before so app.py doesn't change."""
    return _fetch_job(job_id)
