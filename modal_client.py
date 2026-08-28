"""
modal_client.py — VoxCraft Multi-Worker Parallel Client for Chatterbox Voice Cloning
"""

import os
import re
import io
import base64
import requests
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment

CHATTERBOX_ENDPOINT_URL = os.environ.get("MODAL_CLONE_ENDPOINT_URL", "").strip()
_TIMEOUT_SEC = 650
MAX_PARALLEL_WORKERS = 4


def is_configured() -> bool:
    return bool(CHATTERBOX_ENDPOINT_URL)


def _split_into_chunks(text: str, max_chars: int = 150) -> list:
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


def _process_chatterbox_chunk(chunk_tuple):
    index, chunk_text, ref_b64, lang_id, url = chunk_tuple
    payload = {
        "chunk_text": chunk_text,
        "reference_audio_b64": ref_b64,
        "language_id": lang_id
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


def generate_audio(text: str, reference_audio_b64: str, language_id: str = "en") -> dict:
    if not CHATTERBOX_ENDPOINT_URL:
        return {"success": False, "error": "Chatterbox Endpoint URL is not configured."}

    chunks = _split_into_chunks(text, max_chars=150)
    tasks = [(i, chunk, reference_audio_b64, language_id, CHATTERBOX_ENDPOINT_URL) for i, chunk in enumerate(chunks)]

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        results = list(executor.map(_process_chatterbox_chunk, tasks))

    results.sort(key=lambda x: x[0])

    audio_segments = []
    for index, success, data in results:
        if not success:
            return {"success": False, "error": f"Chatterbox Chunk {index+1} failed: {data}"}
        audio_segments.append(data)

    combined = AudioSegment.empty()
    for b in audio_segments:
        seg = AudioSegment.from_file(io.BytesIO(b), format="wav")
        combined = combined.append(seg, crossfade=40) if len(combined) > 0 else seg

    out_buf = io.BytesIO()
    combined.export(out_buf, format="wav")
    audio_b64 = base64.b64encode(out_buf.getvalue()).decode("ascii")

    return {"success": True, "audio_b64": audio_b64, "provider": "chatterbox_parallel"}
