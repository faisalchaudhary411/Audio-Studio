"""
modal_f5tts.py — VoxCraft Multi-Worker Parallel Client for F5-TTS

Hindi/Urdu ONLY. The deployed worker (modal_workers/f5tts/app.py) loads a
Hindi-only checkpoint (SPRINGLab/F5-Hindi-24KHz, CC-BY-4.0 — chosen
specifically because it's commercial-use-safe, unlike the official
SWivid/F5-TTS English/Mandarin checkpoint which is CC-BY-NC-4.0). Sending
plain English text here will not raise an error but will sound wrong,
since the checkpoint's vocab is Devanagari-based. Callers must not route
English requests to this module — see modal_client.py's engine dispatch.
"""

import os
import re
import io
import base64
import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment

F5TTS_ENDPOINT_URL = os.environ.get("MODAL_F5TTS_ENDPOINT_URL", "").strip()
_TIMEOUT_SEC = 650

# REDUCED from 4 to 2: Modal's autoscaler was spinning up idle containers
# (0 inputs) alongside working ones when we flooded it with 4 parallel
# requests. Lower parallelism = fewer container races, more predictable
# routing. Total wall-clock time increases slightly but reliability wins.
MAX_PARALLEL_WORKERS = 2

# Retry failed chunks — transient container crashes/terminations (like the
# "Terminated" status in the dashboard) often succeed on retry.
MAX_RETRIES = 2

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(F5TTS_ENDPOINT_URL)


def _is_valid_wav(data: bytes) -> bool:
    """Validate that bytes are a non-empty, well-formed WAV file.

    Catches the 'empty container response' case where Modal returns
    HTTP 200 with success=True but audio_b64 is minimal/invalid.
    """
    if not data or len(data) < 1024:
        return False
    # RIFF....WAVEfmt  header
    if data[:4] != b'RIFF' or data[8:12] != b'WAVE' or data[12:16] != b'fmt ':
        return False
    return True


def _split_into_chunks(text: str, max_chars: int = 120) -> list:
    sentences = re.split(r'(?<=[.!?؟।॥])\s+', text.strip())
    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) <= max_chars:
            current += " " + sentence if current else sentence
        else:
            if current:
                chunks.append(current.strip())
            current = sentence
    if current:
        chunks.append(current.strip())
    return [c for c in chunks if c.strip()]


def _process_f5tts_chunk(chunk_tuple):
    """Single attempt — no retry here, retry wrapper handles that."""
    index, chunk_text, ref_b64, ref_text, url = chunk_tuple
    payload = {
        "chunk_text": chunk_text,
        "reference_audio_b64": ref_b64,
        "ref_text": ref_text,
    }
    try:
        r = requests.post(url, json=payload, timeout=_TIMEOUT_SEC)
        if r.status_code == 200:
            res = r.json()
            if res.get("success") and res.get("audio_b64"):
                audio_bytes = base64.b64decode(res["audio_b64"])
                if not audio_bytes:
                    return (index, False, "Empty audio data after base64 decode", ref_text)
                if not _is_valid_wav(audio_bytes):
                    logger.error(f"Chunk {index}: Invalid WAV from worker (len={len(audio_bytes)})")
                    return (index, False, f"Invalid WAV data from worker (len={len(audio_bytes)})", ref_text)
                return (index, True, audio_bytes, res.get("ref_text", ref_text))
            err = res.get("error", "Empty chunk output")
            logger.warning(f"Chunk {index}: Worker reported failure: {err}")
            return (index, False, err, ref_text)
        logger.warning(f"Chunk {index}: HTTP {r.status_code}")
        return (index, False, f"HTTP {r.status_code}", ref_text)
    except requests.exceptions.Timeout:
        logger.warning(f"Chunk {index}: Timeout")
        return (index, False, "Timed out reaching the Modal F5-TTS worker.", ref_text)
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Chunk {index}: Connection error: {e}")
        return (index, False, f"Connection error: {e}", ref_text)
    except Exception as e:
        logger.exception(f"Chunk {index}: Unexpected error")
        return (index, False, str(e), ref_text)


def _process_f5tts_chunk_with_retry(chunk_tuple):
    """Process a chunk with exponential-backoff retry."""
    index = chunk_tuple[0]
    last_error = "Unknown error"

    for attempt in range(MAX_RETRIES + 1):
        result = _process_f5tts_chunk(chunk_tuple)
        _, success, data, resolved_ref_text = result
        if success:
            return result
        last_error = data
        if attempt < MAX_RETRIES:
            wait = 2 ** attempt  # 1s, then 2s
            logger.warning(f"Chunk {index} attempt {attempt + 1} failed, retrying in {wait}s: {last_error}")
            time.sleep(wait)
        else:
            logger.error(f"Chunk {index} exhausted all {MAX_RETRIES + 1} attempts: {last_error}")

    return (index, False, last_error, chunk_tuple[3])


def generate_long_audio(text: str, reference_audio_b64: str, ref_text: str = "") -> dict:
    if not F5TTS_ENDPOINT_URL:
        return {"success": False, "error": "F5-TTS Endpoint URL is not configured."}

    chunks = _split_into_chunks(text, max_chars=120)
    if not chunks:
        return {"success": False, "error": "No text to generate."}

    # If the caller didn't supply a transcript, the worker auto-transcribes
    # the reference clip via ASR on every request it gets — running that
    # once here and reusing the result for every remaining chunk avoids
    # paying for (and risking slightly inconsistent) re-transcription on
    # each of N chunks.
    if not ref_text and len(chunks) > 1:
        first_index, success, data, resolved_ref_text = _process_f5tts_chunk_with_retry(
            (0, chunks[0], reference_audio_b64, "", F5TTS_ENDPOINT_URL)
        )
        if not success:
            return {"success": False, "error": f"F5-TTS Chunk 1 failed: {data}"}
        ref_text = resolved_ref_text
        remaining = [(i, chunk, reference_audio_b64, ref_text, F5TTS_ENDPOINT_URL) 
                     for i, chunk in enumerate(chunks) if i > 0]

        # Use as_completed instead of map() so we collect results as they
        # arrive, not in submission order. More importantly, if one chunk
        # fails we know immediately instead of blocking on the slowest.
        results = [(first_index, True, data, ref_text)]
        errors = []

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
            future_to_task = {
                executor.submit(_process_f5tts_chunk_with_retry, task): task 
                for task in remaining
            }
            for future in as_completed(future_to_task):
                idx, success, data, _ = future.result()
                if success:
                    results.append((idx, True, data, ref_text))
                else:
                    errors.append(f"Chunk {idx + 1} failed: {data}")

        if errors:
            # Return partial failure info so caller can decide
            return {"success": False, "error": " | ".join(errors)}
    else:
        tasks = [(i, chunk, reference_audio_b64, ref_text, F5TTS_ENDPOINT_URL) 
                 for i, chunk in enumerate(chunks)]

        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
            future_to_task = {
                executor.submit(_process_f5tts_chunk_with_retry, task): task 
                for task in tasks
            }
            for future in as_completed(future_to_task):
                idx, success, data, resolved_ref_text = future.result()
                if success:
                    results.append((idx, True, data, resolved_ref_text))
                else:
                    errors.append(f"Chunk {idx + 1} failed: {data}")

        if errors:
            return {"success": False, "error": " | ".join(errors)}

        # Extract ref_text from first successful result for consistency
        ref_text = results[0][3] if results else ""

    # Sort by original chunk index to maintain text order
    results.sort(key=lambda x: x[0])

    audio_segments = []
    for index, success, data, _ in results:
        if not success:
            # Should never hit here due to early error return above, but guard
            return {"success": False, "error": f"F5-TTS Chunk {index + 1} failed unexpectedly."}
        audio_segments.append(data)

    # Concatenate with crossfade
    combined = AudioSegment.empty()
    for b in audio_segments:
        seg = AudioSegment.from_file(io.BytesIO(b), format="wav")
        combined = combined.append(seg, crossfade=50) if len(combined) > 0 else seg

    out_buf = io.BytesIO()
    combined.export(out_buf, format="wav")
    final_bytes = out_buf.getvalue()

    # Final validation: ensure combined output is also valid
    if not _is_valid_wav(final_bytes):
        return {"success": False, "error": "Combined audio output is invalid — possible corruption during stitching."}

    audio_b64 = base64.b64encode(final_bytes).decode("ascii")

    return {"success": True, "audio_b64": audio_b64, "provider": "f5tts_parallel"}
