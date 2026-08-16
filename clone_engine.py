"""
clone_engine.py — voice cloning via Chatterbox-Turbo (Resemble AI, MIT
license — genuinely free for commercial use, unlike XTTS-v2/F5-TTS whose
official weights are CC-BY-NC-4.0, non-commercial only).

Runs on Modal (modal_workers/chatterbox/app.py), not on this VPS — a clone
request could otherwise pin the CPU for 10-60+ seconds or exhaust RAM on a
1 vCPU / 2GB VPS shared with the rest of the site.

FIXED: Replaced in-memory _jobs dict with SQLite to survive across
processes/workers. The old _jobs = {} only lived in one process, so polling
requests hitting a different worker always returned None → "Unknown job."
"""

import base64
import os
import sqlite3
import threading
import uuid

import modal_client

# ---------------------------------------------------------------------------
# SQLite persistence — shared across all processes / workers
# ---------------------------------------------------------------------------
DB_PATH = os.environ.get("JOBS_DB_PATH", "/tmp/clone_jobs.db")
_DB_LOCK = threading.Lock()


def _init_db():
    with _DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          TEXT PRIMARY KEY,
                status      TEXT NOT NULL,
                audio       BLOB,
                error       TEXT
            )
        """)
        conn.commit()
        conn.close()


_init_db()


def _save_job(job_id: str, status: str, audio: bytes = None, error: str = None):
    with _DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """INSERT INTO jobs (id, status, audio, error)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   status=excluded.status,
                   audio=excluded.audio,
                   error=excluded.error""",
            (job_id, status, audio, error),
        )
        conn.commit()
        conn.close()


def _get_job(job_id: str):
    with _DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT status, audio, error FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        conn.close()

    if row is None:
        return None
    return {"status": row[0], "audio": row[1], "error": row[2]}


# ---------------------------------------------------------------------------
# Modal clone worker
# ---------------------------------------------------------------------------
def _run_clone_job(job_id: str, text: str, reference_audio_path: str):
    _save_job(job_id, "generating")
    try:
        with open(reference_audio_path, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode("ascii")

        result = modal_client.generate(text, ref_b64)
        if not result.get("success"):
            _save_job(
                job_id,
                "error",
                error=result.get("error", "Generation failed."),
            )
            return

        audio_bytes = base64.b64decode(result["audio_b64"])
        _save_job(job_id, "done", audio=audio_bytes)
    except Exception as exc:
        _save_job(job_id, "error", error=str(exc))


def start_clone_job(text: str, reference_audio_path: str) -> str:
    """Queue a new voice-clone job and return its tracking ID."""
    job_id = uuid.uuid4().hex

    if not modal_client.is_configured():
        _save_job(
            job_id,
            "error",
            error=(
                "Voice cloning isn't configured on this deployment yet — "
                "set MODAL_CLONE_ENDPOINT_URL."
            ),
        )
        return job_id

    _save_job(job_id, "queued")
    thread = threading.Thread(
        target=_run_clone_job,
        args=(job_id, text, reference_audio_path),
        daemon=True,
    )
    thread.start()
    return job_id


def get_job(job_id: str):
    """Return the current status/audio/error dict for a job, or None."""
    return _get_job(job_id)
