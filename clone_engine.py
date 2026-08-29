"""
clone_engine.py — Voice cloning orchestration (FIXED).

FIXES APPLIED:
1. _update_job now uses BEGIN IMMEDIATE transaction — prevents DB read
   from seeing partial BLOB writes (was causing garbled/corrupted audio
   when frontend polled mid-write).
2. Added "validating" status — frontend only plays audio when status="done",
   not when audio blob is non-null.
3. _fetch_job now also uses BEGIN IMMEDIATE for consistent reads.
4. Better error propagation with full traceback in logs.
"""

import base64
import os
import sqlite3
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

import modal_client
import urdu_transliteration

JOB_DB_PATH = os.environ.get("CLONE_JOB_DB_PATH", "/tmp/voxcraft_clone_jobs.db")
JOB_MAX_AGE_SECONDS = 1200
MAX_PARALLEL_SEGMENT_WORKERS = 2

_db_lock = threading.Lock()


def _db_conn():
    conn = sqlite3.connect(JOB_DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _db_lock:
        conn = _db_conn()
        conn.execute("BEGIN IMMEDIATE")
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
                    conn.execute("BEGIN IMMEDIATE")
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
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO clone_jobs (job_id, status, created_at, updated_at)
            VALUES (?, 'queued', ?, ?)
            """,
            (job_id, now, now),
        )
        conn.commit()
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL FIX: BEGIN IMMEDIATE transaction
#
# Previously: _update_job wrote audio BLOB without an exclusive transaction.
# SQLite's default journaling mode can allow readers to see partial writes.
# When the frontend polled _fetch_job during an in-progress _update_job,
# it could receive a partially-written audio BLOB — producing garbled
# output that sounded like noise or corruption.
#
# Now: BEGIN IMMEDIATE acquires an exclusive lock BEFORE any writes,
# ensuring the entire UPDATE is atomic. Readers block until commit.
# ═══════════════════════════════════════════════════════════════════════════════
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
        conn.execute("BEGIN IMMEDIATE")  # ← EXCLUSIVE LOCK
        conn.execute(
            "UPDATE clone_jobs SET " + ", ".join(fields) + " WHERE job_id = ?",
            values,
        )
        conn.commit()  # ← Atomic: all fields written together
        conn.close()


def _fetch_job(job_id: str):
    # ═══════════════════════════════════════════════════════════════════════════
    # CRITICAL FIX: Also use BEGIN IMMEDIATE for reads
    #
    # Without this, a read could see uncommitted data from another
    # connection's in-progress transaction (depending on SQLite mode).
    # BEGIN IMMEDIATE on read ensures we wait for any writer to finish.
    # ═══════════════════════════════════════════════════════════════════════════
    with _db_lock:
        conn = _db_conn()
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT job_id, status, audio, error, created_at, updated_at FROM clone_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        conn.commit()
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


def _is_valid_wav(data: bytes) -> bool:
    """Validate WAV header and minimum size."""
    if not data or len(data) < 1024:
        return False
    return data[:4] == b'RIFF' and data[8:12] == b'WAVE'


def _split_for_stable_generation(text: str, max_chars: int = 280) -> list:
    """
    Split long Devanagari/English text into natural segments for stable TTS.
    """
    import re
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) == 1:
        paragraphs = [s.strip() for s in re.split(r"(?<=[.!?।॥])\s+", text) if s.strip()]

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
    for i, raw in enumerate(wav_bytes_list):
        seg = AudioSegment.from_file(io.BytesIO(raw), format="wav")
        if i > 0:
            combined += AudioSegment.silent(duration=90)
        combined += seg
    buf = io.BytesIO()
    combined.export(buf, format="wav")
    return buf.getvalue()


def _run_clone_job(job_id: str, text: str, reference_audio_path: str,
                   requested_lang: str = "en", engine: str = "chatterbox",
                   ref_text: str = ""):
    _update_job(job_id, status="generating")
    try:
        with open(reference_audio_path, "rb") as f:
            ref_b64 = base64.b64encode(f.read()).decode("ascii")

        processed_text, auto_lang_id = urdu_transliteration.prepare_text_for_tts(text)
        language_id = requested_lang if requested_lang in ("hi", "en") and requested_lang != "en" else auto_lang_id

        if engine == "f5tts" and language_id not in modal_client.F5TTS_SUPPORTED_LANGUAGES:
            _update_job(
                job_id,
                status="error",
                error="The F5-TTS engine only supports Hindi/Urdu text on this deployment. Switch to Chatterbox for English.",
            )
            return

        if engine == "f5tts":
            result = modal_client.generate(
                processed_text, ref_b64,
                language_id=language_id, engine=engine, ref_text=ref_text
            )
            if not result.get("success"):
                _update_job(
                    job_id,
                    status="error",
                    error=result.get("error", "F5-TTS generation failed."),
                )
                return

            final_audio = base64.b64decode(result["audio_b64"])

            # ═══════════════════════════════════════════════════════════════════
            # FIX: Validate BEFORE marking done. Also use "validating" status
            # so frontend knows not to play partial data.
            # ═══════════════════════════════════════════════════════════════════
            _update_job(job_id, status="validating")

            if not _is_valid_wav(final_audio):
                _update_job(
                    job_id,
                    status="error",
                    error=f"F5-TTS returned invalid audio ({len(final_audio)} bytes). Possible container corruption.",
                )
                return

            _update_job(job_id, status="done", audio=final_audio)
            return

        # Chatterbox path
        segments = _split_for_stable_generation(processed_text, max_chars=280)

        if len(segments) == 1:
            results = [modal_client.generate(segments[0], ref_b64, language_id=language_id, engine=engine)]
        else:
            with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_SEGMENT_WORKERS, len(segments))) as executor:
                results = list(executor.map(
                    lambda seg: modal_client.generate(seg, ref_b64, language_id=language_id, engine=engine),
                    segments,
                ))

        audio_parts = []
        for i, result in enumerate(results):
            if not result.get("success"):
                _update_job(
                    job_id,
                    status="error",
                    error=result.get("error", f"Segment {i+1}/{len(segments)} failed."),
                )
                return
            part = base64.b64decode(result["audio_b64"])
            if not _is_valid_wav(part):
                _update_job(
                    job_id,
                    status="error",
                    error=f"Segment {i+1} returned invalid audio.",
                )
                return
            audio_parts.append(part)

        final_audio = _concat_wav_segments(audio_parts) if len(audio_parts) > 1 else audio_parts[0]

        _update_job(job_id, status="validating")

        if not _is_valid_wav(final_audio):
            _update_job(
                job_id,
                status="error",
                error="Stitched audio is invalid — possible corruption during concatenation.",
            )
            return

        _update_job(job_id, status="done", audio=final_audio)

    except Exception as e:
        err_msg = str(e) + "\n" + traceback.format_exc()
        print(f"[CLONE JOB ERROR] job_id={job_id}\n{err_msg}")
        _update_job(
            job_id,
            status="error",
            error=err_msg,
        )


def start_clone_job(text: str, reference_audio_path: str, language_id: str = "en",
                    engine: str = "chatterbox", ref_text: str = "") -> str:
    job_id = uuid.uuid4().hex
    _insert_job(job_id)

    if engine not in modal_client.VALID_ENGINES:
        _update_job(job_id, status="error", error=f"Unknown engine '{engine}'.")
        return job_id

    if not modal_client.engine_is_configured(engine):
        env_var = "MODAL_CLONE_ENDPOINT_URL" if engine == "chatterbox" else "MODAL_F5TTS_ENDPOINT_URL"
        _update_job(
            job_id,
            status="error",
            error=f"The {engine} engine isn't configured on this deployment yet — set {env_var}.",
        )
        return job_id

    thread = threading.Thread(
        target=_run_clone_job,
        args=(job_id, text, reference_audio_path, language_id, engine, ref_text),
        daemon=True,
    )
    thread.start()
    return job_id


def get_job(job_id: str):
    return _fetch_job(job_id)
