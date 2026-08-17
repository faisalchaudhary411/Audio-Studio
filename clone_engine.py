"""
clone_engine.py — voice cloning via Chatterbox Multilingual (Resemble AI, MIT
license — genuinely free for commercial use, unlike XTTS-v2/F5-TTS whose
official weights are CC-BY-NC-4.0, non-commercial only).

Runs on Modal (modal_workers/chatterbox/app.py), not on this VPS — a clone
request could otherwise pin the CPU for 10-60+ seconds or exhaust RAM on a
1 vCPU / 2GB VPS shared with the rest of the site.

CHANGED: originally used RunPod (async /run + /status polling), then Modal
with an in-memory dict. Switched to SQLite-backed job storage because the
in-memory dict caused the "Unknown job" bug under gunicorn: each worker
process had its own _jobs dict, so a job created on Worker A was invisible
to Worker B when the frontend polled /api/clone/status/<job_id>.

SQLite lives on disk at /tmp/voxcraft_clone_jobs.db, so it's shared across
all gunicorn workers and survives worker restarts. Jobs auto-expire after
10 minutes to prevent unbounded DB growth.

Same public interface (start_clone_job / get_job) — app.py never changes.
"""

import base64
import os
import sqlite3
import threading
import time
import traceback
import uuid

import modal_client
import urdu_transliteration

# ── Configuration ──────────────────────────────────────────────────────────
JOB_DB_PATH = os.environ.get("CLONE_JOB_DB_PATH", "/tmp/voxcraft_clone_jobs.db")
JOB_MAX_AGE_SECONDS = 600  # 10 min — old jobs cleaned up so the DB doesn't grow forever

# ── SQLite job store ───────────────────────────────────────────────────────
# Each gunicorn worker is a separate process with its own memory space.
# An in-memory dict (the old _jobs = {}) meant Worker A created the job,
# Worker B polled for it — and saw nothing. SQLite on disk is shared by
# all processes, fixing this without adding Redis or another service.

_db_lock = threading.Lock()


def _db_conn():
    """Return a fresh SQLite connection. SQLite connections are NOT thread-safe
    across threads, so each call gets its own. The DB file itself is process-safe
    (OS-level file locking), but we add _db_lock on writes to serialize them
    and avoid "database is locked" errors under concurrent load."""
    conn = sqlite3.connect(JOB_DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    """Create the jobs table if it doesn't exist yet."""
    with _db_lock:
        conn = _db_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clone_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'queued',
                audio BLOB,
                error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_clone_jobs_created ON clone_jobs(created_at)")
        conn.commit()
        conn.close()


# Run once at import time — safe because CREATE TABLE IF NOT EXISTS is idempotent
_init_db()


# ── Background sweeper ─────────────────────────────────────────────────────
# Old jobs pile up forever if we never clean them. A daemon thread sweeps
# every 60 seconds. Non-fatal if it fails — worst case the DB grows slowly.

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
                    conn.execute("DELETE FROM clone_jobs WHERE created_at < ?", (cutoff,))
                    conn.commit()
                    conn.close()
            except Exception:
                pass  # don't crash the sweeper thread

    _sweep_thread = threading.Thread(target=_sweep_loop, daemon=True)
    _sweep_thread.start()


_start_sweep_thread()


# ── Low-level DB helpers ───────────────────────────────────────────────────

def _insert_job(job_id: str) -> None:
    now = time.time()
    with _db_lock:
        conn = _db_conn()
        conn.execute(
            """
            INSERT INTO clone_jobs (job_id, status, created_at, updated_at)
            VALUES (?, 'queued', ?, ?)
            """,
            (job_id, now, now),
        )
        conn.commit()
        conn.close()


def _update_job(job_id: str, status: str = None, audio: bytes = None, error: str = None) -> None:
    """Update one or more fields on a job. Only non-None fields are written."""
    fields = []
    values = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if audio is not None:
        fields.append("audio = ?")
        values.append(audio)
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
        conn.execute(
            "UPDATE clone_jobs SET " + ", ".join(fields) + " WHERE job_id = ?",
            values,
        )
        conn.commit()
        conn.close()


def _fetch_job(job_id: str):
    """Return a dict matching the old in-memory shape, or None if not found."""
    conn = _db_conn()
    row = conn.execute(
        "SELECT job_id, status, audio, error, created_at, updated_at FROM clone_jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "job_id": row["job_id"],
        "status": row["status"],
        "audio": row["audio"],
        "error": row["error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ── Core clone logic ───────────────────────────────────────────────────────

def _run_clone_job(job_id: str, text: str, reference_audio_path: str):
    _update_job(job_id, status="generating")
    try:
        with open(reference_audio_path, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode("ascii")

        # Chatterbox Multilingual has no Urdu mode. Urdu and Hindi are the
        # same spoken language (Hindustani), differing only in script — so
        # Urdu text gets transliterated to Devanagari and generated via the
        # Hindi language_id, which produces correctly-pronounced audio.
        # See urdu_transliteration.py for the full explanation and the
        # licensing reason this is hand-built rather than using an
        # existing library.
        #
        # prepare_text_for_tts() auto-detects language and handles transliteration.
        processed_text, language_id = urdu_transliteration.prepare_text_for_tts(text)

        result = modal_client.generate(processed_text, ref_b64, language_id=language_id)
        if not result.get("success"):
            _update_job(
                job_id,
                status="error",
                error=result.get("error", "Generation failed."),
            )
            return

        _update_job(
            job_id,
            status="done",
            audio=base64.b64decode(result["audio_b64"]),
        )
    except Exception as e:
        err_msg = str(e) + "\n" + traceback.format_exc()
        _update_job(
            job_id,
            status="error",
            error=err_msg,
        )


# ── Public API (unchanged interface — app.py calls these) ──────────────────

def start_clone_job(text: str, reference_audio_path: str, language_id: str = "en") -> str:
    """Queue a new clone job and return its ID immediately.

    The actual generation runs in a background thread so the HTTP response
    returns instantly — the frontend polls /api/clone/status/<job_id>.

    NOTE: language_id is accepted for API compatibility (Flask passes it)
    but is currently ignored because urdu_transliteration.prepare_text_for_tts()
    auto-detects the language from the text content. If you later want to
    force a specific language, pass it through to _run_clone_job here.
    """
    job_id = uuid.uuid4().hex
    _insert_job(job_id)

    if not modal_client.is_configured():
        _update_job(
            job_id,
            status="error",
            error=(
                "Voice cloning isn't configured on this deployment yet — "
                "set MODAL_CLONE_ENDPOINT_URL."
            ),
        )
        return job_id

    thread = threading.Thread(
        target=_run_clone_job,
        args=(job_id, text, reference_audio_path),
        daemon=True,
    )
    thread.start()
    return job_id


def get_job(job_id: str):
    """Return job dict (or None) — same shape as the old in-memory version
    so api_clone_status in app.py doesn't need to change."""
    return _fetch_job(job_id)
