"""
modal_f5tts.py — VoxCraft Multi-Worker Parallel Client for F5-TTS

Hindi/Urdu ONLY. The deployed worker (modal_workers/f5tts/app.py) loads a
Hindi-only checkpoint (SPRINGLab/F5-Hindi-24KHz, CC-BY-4.0 — chosen
specifically because it's commercial-use-safe, unlike the official
SWivid/F5-TTS English/Mandarin checkpoint which is CC-BY-NC-4.0). Sending
plain English text here will not raise an error but will sound wrong,
since the checkpoint's vocab is Devanagari-based. Callers must not route
English requests to this module — see modal_client.py's engine dispatch.

ref_text (optional): exact transcript of the reference audio. When provided
the worker skips ASR and uses this text for voice conditioning. Strongly
recommended — automatic ASR often produces imperfect transcripts that
cause the model to output noise instead of speech.
"""

import os
import re
import io
import base64
import requests
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment

F5TTS_ENDPOINT_URL = os.environ.get("MODAL_F5TTS_ENDPOINT_URL", "").strip()
_TIMEOUT_SEC = 650
MAX_PARALLEL_WORKERS = 4


def is_configured() -> bool:
    return bool(F5TTS_ENDPOINT_URL)


def _split_into_chunks(text: str, max_chars: int = 300) -> list:
    sentences = re.split(r'(?<=[.!?۔؟।])\s+', text.strip())
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
    index, chunk_text, ref_b64, ref_text, url = chunk_tuple
    payload = {
        "chunk_text": chunk_text,
        "reference_audio_b64": ref_b64,
        "ref_text": ref_text or "",
    }
    try:
        r = requests.post(url, json=payload, timeout=_TIMEOUT_SEC)
        if r.status_code == 200:
            res = r.json()
            if res.get("success") and res.get("audio_b64"):
                return (index, True, base64.b64decode(res["audio_b64"]))
            return (index, False, res.get("error", "Empty chunk output"))
        return (index, False, f"HTTP {r.status_code}")
    except Exception as e:
        return (index, False, str(e))


def generate_long_audio(text: str, reference_audio_b64: str, ref_text: str = "") -> dict:
    if not F5TTS_ENDPOINT_URL:
        return {"success": False, "error": "F5-TTS Endpoint URL is not configured."}

    chunks = _split_into_chunks(text, max_chars=300)
    if not chunks:
        return {"success": False, "error": "No text chunks to generate."}

    tasks = [
        (i, chunk, reference_audio_b64, ref_text, F5TTS_ENDPOINT_URL)
        for i, chunk in enumerate(chunks)
    ]

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        results = list(executor.map(_process_f5tts_chunk, tasks))

    results.sort(key=lambda x: x[0])

    audio_segments = []
    for index, success, data in results:
        if not success:
            return {"success": False, "error": f"F5-TTS Chunk {index+1} failed: {data}"}
        audio_segments.append(data)

    combined = AudioSegment.empty()
    for b in audio_segments:
        seg = AudioSegment.from_file(io.BytesIO(b), format="wav")
        combined = combined.append(seg, crossfade=50) if len(combined) > 0 else seg

    out_buf = io.BytesIO()
    combined.export(out_buf, format="wav")
    audio_b64 = base64.b64encode(out_buf.getvalue()).decode("ascii")

    return {"success": True, "audio_b64": audio_b64, "provider": "f5tts_parallel"}
