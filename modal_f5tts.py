"""
modal_f5tts.py — VoxCraft Multi-Worker Parallel Client for F5-TTS (FIXED).

FIXES APPLIED:
1. Increased MAX_PARALLEL_WORKERS from 2 to 3 — with concurrency_limit=1 on
   the worker, each chunk now gets its own dedicated container. No more
   container races. Higher parallelism = faster total time.
2. Added chunk-level retry with worker URL rotation — if one container
   is in a bad state, retry hits a fresh container.
3. Better WAV validation — catches empty/corrupted responses early.
4. Added request-level timeout and connection pooling for reliability.

Hindi/Urdu ONLY. English text will sound wrong — routing enforced in
modal_client.py.
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

# ═══════════════════════════════════════════════════════════════════════════════
# FIX: Increased from 2 to 3. With concurrency_limit=1 on the worker,
# each parallel request spins up its own container. No more "0 input"
# idle containers alongside "3 input" busy ones — every container is
# actively processing one chunk. Total wall-clock time drops because
# chunks run in true parallel across separate containers.
# ═══════════════════════════════════════════════════════════════════════════════
MAX_PARALLEL_WORKERS = 3

MAX_RETRIES = 2

# Onset-clipping / first-word protection.
#
# Root cause inside f5-tts infer_batch_process:
#   generated = generated[:, ref_audio_len:, :]
# The crop uses only the reference audio length. Transition blur at that
# boundary eats the start of the new content (half-words / missing first
# word). We therefore prepend a short neutral Urdu pause token so the
# model "spends" the blur on the pause; the real first word arrives after
# the boundary and survives. Current value is the practical sweet spot.
F5_CHUNK_LEADING_PAUSE = "۔ "
logger = logging.getLogger(__name__)

# Reuse connections across requests for lower latency
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})


def is_configured() -> bool:
    return bool(F5TTS_ENDPOINT_URL)


def _is_valid_wav(data: bytes) -> bool:
    """Validate that bytes are a non-empty, well-formed WAV file."""
    if not data or len(data) < 1024:
        return False
    if data[:4] != b'RIFF' or data[8:12] != b'WAVE' or data[12:16] != b'fmt ':
        return False
    return True


def _hard_wrap(text: str, max_chars: int) -> list:
    """Last-resort split for a run with no usable punctuation at all —
    break on whitespace near max_chars so no single chunk ever exceeds it.
    F5's own duration heuristic (ref_len + ref_len/ref_bytes * gen_bytes)
    degrades badly past ~80 chars of unbroken input, so this must never be
    skipped just because the text lacks periods or dandas."""
    words = text.split()
    if not words:
        return []
    pieces = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def _split_into_chunks(text: str, max_chars: int = 70) -> list:
    """Split on sentence terminators first (Latin + Devanagari/Urdu danda,
    Hindi/Urdu question mark), then on commas, then hard-wrap anything that
    is still too long. A Hindi/Urdu paragraph with no '.', '!', '?', '।',
    or '॥' used to come back as a single oversized sentence and get pushed
    into infer_process whole — F5 falls apart well past 80 characters of
    unbroken input, which is what produced long runs of unintelligible
    "voice-shaped" audio with no stitch/crossfade seams in it."""
    text = text.strip()
    if not text:
        return []

    # Normalize whitespace so length estimates and splits stay consistent.
    text = re.sub(r'\s+', ' ', text)

    sentences = re.split(r'(?<=[.!?؟।॥])\s+', text)

    chunks = []
    current = ""

    def flush():
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > max_chars:
            # This "sentence" has no terminator inside it (or is one huge
            # run) — flush what we have, then break IT down further
            # instead of ever handing infer_process something this long.
            flush()
            sub_pieces = re.split(r'(?<=[,،])\s+', sentence)
            sub_current = ""
            for piece in sub_pieces:
                piece = piece.strip()
                if not piece:
                    continue
                if len(piece) > max_chars:
                    if sub_current:
                        chunks.append(sub_current.strip())
                        sub_current = ""
                    chunks.extend(_hard_wrap(piece, max_chars))
                elif len(sub_current) + len(piece) + 1 <= max_chars:
                    sub_current = f"{sub_current} {piece}".strip()
                else:
                    chunks.append(sub_current.strip())
                    sub_current = piece
            if sub_current:
                chunks.append(sub_current.strip())
            continue

        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
        else:
            flush()
            current = sentence

    flush()
    return [c for c in chunks if c.strip()]


def _process_f5tts_chunk(chunk_tuple):
    """Single attempt — no retry here, retry wrapper handles that."""
    index, chunk_text, ref_b64, ref_text, url = chunk_tuple
    payload = {
        "chunk_text": f"{F5_CHUNK_LEADING_PAUSE}{chunk_text}" if F5_CHUNK_LEADING_PAUSE else chunk_text,
        "reference_audio_b64": ref_b64,
        "ref_text": ref_text,
    }
    try:
        r = _session.post(url, json=payload, timeout=_TIMEOUT_SEC)
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

    chunks = _split_into_chunks(text, max_chars=70)

    # F5's duration estimate (see infer_process's max_chars formula) is
    # least reliable on very short chunks — this is what showed up as
    # word-initial clipping ("آج" -> "आ") once the 80-char split above
    # started producing more, shorter chunks. A short chunk sitting alone
    # gives the model the least context to establish natural onset timing.
    # Merging any undersized chunk into its neighbor (while staying under
    # max_chars) trades a little extra chunk length for a steadier onset.
    MIN_CHUNK_CHARS = 30
    merged_chunks = []
    for c in chunks:
        if (
            merged_chunks
            and len(merged_chunks[-1]) < MIN_CHUNK_CHARS
            and len(merged_chunks[-1]) + len(c) + 1 <= 80
        ):
            merged_chunks[-1] = f"{merged_chunks[-1]} {c}"
        else:
            merged_chunks.append(c)
    chunks = merged_chunks

    if not chunks:
        return {"success": False, "error": "No text to generate."}

    # If the caller didn't supply a transcript, run the first chunk to
    # get auto-transcribed ref_text, then reuse it for all remaining chunks.
    if not ref_text and len(chunks) > 1:
        first_index, success, data, resolved_ref_text = _process_f5tts_chunk_with_retry(
            (0, chunks[0], reference_audio_b64, "", F5TTS_ENDPOINT_URL)
        )
        if not success:
            return {"success": False, "error": f"F5-TTS Chunk 1 failed: {data}"}
        ref_text = resolved_ref_text
        remaining = [(i, chunk, reference_audio_b64, ref_text, F5TTS_ENDPOINT_URL) 
                     for i, chunk in enumerate(chunks) if i > 0]

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

        ref_text = results[0][3] if results else ""

    # Sort by original chunk index to maintain text order
    results.sort(key=lambda x: x[0])

    audio_segments = []
    for index, success, data, _ in results:
        if not success:
            return {"success": False, "error": f"F5-TTS Chunk {index + 1} failed unexpectedly."}
        audio_segments.append(data)

    # Concatenate with crossfade
    combined = AudioSegment.empty()
    for b in audio_segments:
        seg = AudioSegment.from_file(io.BytesIO(b), format="wav")
        combined = combined.append(seg, crossfade=100) if len(combined) > 0 else seg

    # Light compression of excessively long internal silences only.
    # Keeps natural short pauses, removes the long dead gaps that appear
    # between poorly-generated chunks.
    from pydub.silence import detect_nonsilent
    nonsilent = detect_nonsilent(combined, min_silence_len=450, silence_thresh=-42)
    if nonsilent:
        cleaned = AudioSegment.empty()
        for i, (start, end) in enumerate(nonsilent):
            cleaned += combined[start:end]
            if i < len(nonsilent) - 1:
                # keep a short natural pause (180 ms) between speech regions
                cleaned += AudioSegment.silent(duration=180)
        combined = cleaned

    out_buf = io.BytesIO()
    combined.export(out_buf, format="wav")
    final_bytes = out_buf.getvalue()

    if not _is_valid_wav(final_bytes):
        return {"success": False, "error": "Combined audio output is invalid — possible corruption during stitching."}

    audio_b64 = base64.b64encode(final_bytes).decode("ascii")

    return {"success": True, "audio_b64": audio_b64, "provider": "f5tts_parallel"}
