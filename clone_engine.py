"""
clone_engine.py — Voice cloning orchestration via SQLite job queue & Modal client.
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

JOB_DB_PATH = os.environ.get("CLONE_JOB_DB_PATH", "/tmp/voxcraft_clone_jobs.db")
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
                    conn.execute("DELETE FROM clone_jobs WHERE created_at < ?", (cutoff,))
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
            """
            INSERT INTO clone_jobs (job_id, status, created_at, updated_at)
            VALUES (?, 'queued', ?, ?)
            """,
            (job_id, now, now),
        )
        conn.commit()
        conn.close()


def _update_job(job_id: str, status: str = None, audio: bytes = None, error: str = None) -> None:
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


def _run_clone_job(job_id: str, text: str, reference_audio_path: str, requested_lang: str = "en"):
    _update_job(job_id, status="generating")
    try:
        with open(reference_audio_path, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode("ascii")

        processed_text, auto_lang_id = urdu_transliteration.prepare_text_for_tts(text)
        language_id = requested_lang if requested_lang in ("hi", "en") and requested_lang != "en" else auto_lang_id

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


def start_clone_job(text: str, reference_audio_path: str, language_id: str = "en") -> str:
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
        args=(job_id, text, reference_audio_path, language_id),
        daemon=True,
    )
    thread.start()
    return job_id


def get_job(job_id: str):
    return _fetch_job(job_id)
