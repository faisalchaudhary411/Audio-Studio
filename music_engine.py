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

BUG FIX HISTORY:
- v1: Used raw requests to /v1/models/lucataco/ace-step/predictions with wrong
  param names ("tags" instead of "prompt"), causing 404.
- v2: Switched to official replicate client, but still wrong params.
- v3 (this): Fixed param names to match Replicate schema: "prompt" (not "tags"),
  "duration" as number, "lyrics" optional. Also switched to SQLite job store.
"""

import os
import sqlite3
import threading
import time
import traceback
import uuid

# ── Replicate client ───────────────────────────────────────────────────────
# The official client handles auth, model resolution, polling, and errors.
# Install: pip install replicate
# It reads REPLICATE_API_TOKEN from os.environ automatically.

try:
    import replicate
    _REPLICATE_AVAILABLE = True
except ImportError:
    replicate = None
    _REPLICATE_AVAILABLE = False

REPLICATE_MODEL = "lucataco/ace-step"

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

def _run_music_job(job_id: str, prompt: str, lyrics: str, duration: int, seed: int = None):
    """Run music generation via Replicate's ACE-Step model.

    Replicate schema for lucataco/ace-step:
    - prompt (str, required): Music description
    - duration (float, default 60): Seconds, max 240
    - lyrics (str, optional): Lyrics or "[inst]" for instrumental
    - seed (int, optional): Random seed
    """
    _update_job(job_id, status="starting")
    try:
        if not _REPLICATE_AVAILABLE:
            _update_job(
                job_id,
                status="error",
                error="The `replicate` Python package is not installed. Run: pip install replicate",
            )
            return

        # Build input matching Replicate's schema exactly
        input_payload = {
            "prompt": prompt,
            "duration": min(duration, 240),  # Replicate caps at 240s
        }

        # Only add lyrics if provided; "[inst]" means instrumental
        if lyrics and lyrics.strip():
            input_payload["lyrics"] = lyrics.strip()

        if seed is not None:
            input_payload["seed"] = seed

        _update_job(job_id, status="generating")

        # Replicate API caps wait at 60 seconds (HTTP 422 if higher).
        # ACE-Step typically completes in ~21s, but queue delays can push
        # it past 60s. Strategy: create prediction, then poll manually.
        prediction = replicate.predictions.create(
            model=REPLICATE_MODEL,
            input=input_payload,
        )

        # Poll until done, failed, or timeout (~3 minutes total)
        for _ in range(90):  # 90 * 2s = 180s = 3 minutes
            prediction.reload()
            status = prediction.status

            if status == "succeeded":
                output = prediction.output
                if not output:
                    _update_job(job_id, status="error", error="Replicate returned no audio output.")
                    return

                # Handle both list and single output
                first_output = output[0] if isinstance(output, list) else output
                if hasattr(first_output, "url"):
                    audio_url = first_output.url()
                    audio_bytes = first_output.read()
                elif hasattr(first_output, "read"):
                    audio_url = None
                    audio_bytes = first_output.read()
                else:
                    audio_url = str(first_output)
                    import requests
                    audio_bytes = requests.get(audio_url, timeout=30).content

                _update_job(
                    job_id,
                    status="done",
                    audio=audio_bytes,
                    audio_url=audio_url,
                )
                return

            if status in ("failed", "canceled"):
                _update_job(
                    job_id,
                    status="error",
                    error=prediction.error or f"Generation {status}.",
                )
                return

            time.sleep(2)

        # Timeout after 3 minutes
        _update_job(
            job_id,
            status="error",
            error="Timed out waiting for Replicate (took longer than 3 minutes).",
        )
    except replicate.exceptions.ReplicateError as e:
        _update_job(job_id, status="error", error=f"Replicate API error: {e}")
    except Exception as e:
        err_msg = str(e) + "\n" + traceback.format_exc()
        _update_job(job_id, status="error", error=err_msg)


# ── Public API ─────────────────────────────────────────────────────────────

def start_music_job(tags: str, lyrics: str = "", duration: int = 60, seed: int = None) -> dict:
    """Queue a music generation job and return its ID immediately.

    NOTE: Parameter is still called 'tags' for backward compatibility with
    app.py, but it's mapped to 'prompt' for the Replicate API.
    """
    job_id = uuid.uuid4().hex
    _insert_job(job_id)

    if not _REPLICATE_AVAILABLE:
        _update_job(
            job_id,
            status="error",
            error="The `replicate` Python package is not installed. Add to requirements.txt: replicate",
        )
        return {"job_id": job_id}

    # Check token visibility at call time (not import time)
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        _update_job(
            job_id,
            status="error",
            error=(
                "REPLICATE_API_TOKEN is not set. "
                "Add it to your environment and restart the gunicorn service. "
                "For systemd: sudo systemctl edit voxcraft --force, add [Service] Environment=REPLICATE_API_TOKEN=your_token, then sudo systemctl daemon-reload && sudo systemctl restart voxcraft"
            ),
        )
        return {"job_id": job_id}

    # Map 'tags' (old param name) to 'prompt' (Replicate's param name)
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