"""
music_engine.py — music generation via self-hosted ACE-Step 1.5 running on
Modal GPU (modal_workers/ace_step/app.py), reached through music_client.py.

CHANGED: migrated off Replicate's hosted lucataco/ace-step model (~$0.02-0.03
per generation, billed per-call no matter how small the request). Same
reasoning as the earlier clone_engine.py migration from RunPod to Modal:
self-hosting on Modal means you pay for GPU-seconds actually used, and the
container scales to zero between requests. See modal_workers/ace_step/app.py
for the full migration rationale.

Still gated Pro+-only in app.py — GPU-seconds aren't free, just cheaper and
usage-proportional instead of a flat per-call vendor fee.

Job store: identical SQLite pattern to clone_engine.py (see that file's
docstring for why an in-memory dict breaks under multiple gunicorn worker
processes — same fix applies here).

Public interface (start_music_job / get_job) is unchanged from the Replicate
version, so app.py's /api/music/* routes and static/js/music.js don't need
to change.
"""

import base64
import os
import sqlite3
import threading
import time
import traceback
import uuid

import music_client

# ── SQLite job store (same pattern as clone_engine.py) ─────────────────────

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
                audio_format TEXT,
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
                pass  # don't crash the sweeper thread

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


def _update_job(job_id: str, status: str = None, audio: bytes = None,
                 audio_format: str = None, error: str = None) -> None:
    fields = []
    values = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if audio is not None:
        fields.append("audio = ?")
        values.append(audio)
    if audio_format is not None:
        fields.append("audio_format = ?")
        values.append(audio_format)
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
        "SELECT job_id, status, audio, audio_format, error, created_at, updated_at "
        "FROM music_jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "job_id": row["job_id"],
        "status": row["status"],
        "audio": row["audio"],
        "audio_format": row["audio_format"],
        "error": row["error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ── Core music logic ───────────────────────────────────────────────────────

def _run_music_job(job_id: str, prompt: str, lyrics: str, duration: int, seed: int = None):
    _update_job(job_id, status="generating")
    try:
        # "wav" matches static/js/music.js, which hardcodes
        # `data:audio/wav;base64,...` for the <audio> src and download link —
        # keeping wav here avoids touching the frontend.
        result = music_client.generate(
            prompt, lyrics, duration=float(duration), seed=seed, audio_format="wav"
        )
        if not result.get("success"):
            _update_job(job_id, status="error", error=result.get("error", "Generation failed."))
            return

        _update_job(
            job_id,
            status="done",
            audio=base64.b64decode(result["audio_b64"]),
            audio_format=result.get("audio_format", "wav"),
        )
    except Exception as e:
        err_msg = str(e) + "\n" + traceback.format_exc()
        _update_job(job_id, status="error", error=err_msg)


# ── Public API (unchanged interface — app.py calls these) ──────────────────

def start_music_job(tags: str, lyrics: str = "", duration: int = 60, seed: int = None) -> dict:
    """Queue a music generation job and return its ID immediately.

    NOTE: parameter is still called 'tags' for backward compatibility with
    app.py — it's mapped to ACE-Step's 'prompt'/caption field.
    """
    job_id = uuid.uuid4().hex
    _insert_job(job_id)

    if not music_client.is_configured():
        _update_job(
            job_id,
            status="error",
            error=(
                "Music generation isn't configured on this deployment yet. "
                "Deploy modal_workers/ace_step/app.py to Modal, then set "
                "MODAL_MUSIC_ENDPOINT_URL on the VPS and restart the voxcraft service."
            ),
        )
        return {"job_id": job_id}

    prompt = tags if tags else "instrumental music"

    thread = threading.Thread(
        target=_run_music_job,
        args=(job_id, prompt, lyrics, duration, seed),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


def get_job(job_id: str):
    """Return job dict (or None) — same shape as before so app.py doesn't change."""
    return _fetch_job(job_id)
