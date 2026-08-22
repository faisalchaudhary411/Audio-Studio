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
# Was 600s — exactly equal to Modal's own worker timeout (see
# modal_workers/chatterbox/app.py), with zero margin for cold-start (20-60s)
# on top. A legitimately slow job could get swept out of the DB right as it
# finishes, so the frontend's polling loop finds nothing even though Modal
# succeeded. Raised to give real headroom above the worst case.
JOB_MAX_AGE_SECONDS = 1200

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


def _split_for_stable_generation(text: str, max_chars: int = 380) -> list:
    """
    Split long Devanagari/English text into natural segments for stable TTS.
    Prefers paragraph breaks, then sentence boundaries.
    Keeps each segment under max_chars for commercial quality.
    """
    import re
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    # First try paragraph breaks
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) == 1:
        # Fall back to sentence boundaries
        paragraphs = [s.strip() for s in re.split(r"(?<=[.!?।؟])\s+", text) if s.strip()]

    segments = []
    current = ""
    for part in paragraphs:
        candidate = (current + " " + part).strip() if current else part
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                segments.append(current)
            if len(part) <= max_chars:
                current = part
            else:
                # Hard split long sentence by words
                words = part.split()
                piece = ""
                for w in words:
                    cand = (piece + " " + w).strip() if piece else w
                    if len(cand) <= max_chars:
                        piece = cand
                    else:
                        if piece:
                            segments.append(piece)
                        piece = w
                current = piece
    if current:
        segments.append(current)
    return [s for s in segments if s.strip()]


def _concat_wav_segments(wav_bytes_list: list) -> bytes:
    """Concatenate multiple WAV byte strings into one using pydub."""
    from pydub import AudioSegment
    import io

    if not wav_bytes_list:
        return b""
    if len(wav_bytes_list) == 1:
        return wav_bytes_list[0]

    combined = AudioSegment.empty()
    for raw in wav_bytes_list:
        seg = AudioSegment.from_file(io.BytesIO(raw), format="wav")
        # Small crossfade-like silence between segments for natural flow
        combined += seg + AudioSegment.silent(duration=180)
    buf = io.BytesIO()
    combined.export(buf, format="wav")
    return buf.getvalue()


def _run_clone_job(job_id: str, text: str, reference_audio_path: str, requested_lang: str = "en"):
    _update_job(job_id, status="generating")
    try:
        with open(reference_audio_path, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode("ascii")

        processed_text, auto_lang_id = urdu_transliteration.prepare_text_for_tts(text)
        language_id = requested_lang if requested_lang in ("hi", "en") and requested_lang != "en" else auto_lang_id

        # Commercial: split long text into stable segments, generate each, then stitch
        segments = _split_for_stable_generation(processed_text, max_chars=380)
        audio_parts = []

        for i, segment in enumerate(segments):
            result = modal_client.generate(segment, ref_b64, language_id=language_id)
            if not result.get("success"):
                _update_job(
                    job_id,
                    status="error",
                    error=result.get("error", f"Segment {i+1}/{len(segments)} failed."),
                )
                return
            audio_parts.append(base64.b64decode(result["audio_b64"]))

        final_audio = _concat_wav_segments(audio_parts) if len(audio_parts) > 1 else audio_parts[0]

        _update_job(
            job_id,
            status="done",
            audio=final_audio,
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
