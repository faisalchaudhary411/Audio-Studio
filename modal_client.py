"""
modal_client.py — VoxCraft Multi-Model Parallel Dispatcher

Routes:
- Script < 2000 chars  -> Multi-Worker Chatterbox (Modal Parallel GPUs)
- Script >= 2000 chars -> Multi-Worker F5-TTS (Modal Parallel GPUs)
- Fallback System      -> Cartesia API (Triggers automatically if CARTESIA_API_KEY is active)
"""

import os
import re
import io
import base64
import requests
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment

CHATTERBOX_ENDPOINT_URL = os.environ.get("MODAL_CLONE_ENDPOINT_URL", "").strip()
F5TTS_ENDPOINT_URL = os.environ.get("MODAL_F5TTS_ENDPOINT_URL", "").strip()

CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY", "").strip()
CARTESIA_VOICE_ID = os.environ.get("CARTESIA_VOICE_ID", "a0e16877-e166-415c-9d66-8d0092ad3624").strip()

_TIMEOUT_SEC = 650
MAX_PARALLEL_WORKERS = 4


def is_configured() -> bool:
    return bool(CHATTERBOX_ENDPOINT_URL or F5TTS_ENDPOINT_URL or CARTESIA_API_KEY)


def _split_into_chunks(text: str, max_chars: int = 180) -> list:
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


def _call_cartesia_fallback(text: str) -> dict:
    if not CARTESIA_API_KEY:
        return {"success": False, "error": "Cartesia API Key not configured."}
    
    url = "https://api.cartesia.ai/tts/bytes"
    headers = {
        "X-API-Key": CARTESIA_API_KEY,
        "Cartesia-Version": "2024-06-10",
        "Content-Type": "application/json"
    }
    payload = {
        "model_id": "sonic-english",
        "transcript": text,
        "voice": {"mode": "id", "id": CARTESIA_VOICE_ID},
        "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 24000}
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        if r.status_code == 200:
            audio_b64 = base64.b64encode(r.content).decode("ascii")
            return {"success": True, "audio_b64": audio_b64, "provider": "cartesia_fallback"}
        return {"success": False, "error": f"Cartesia HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {"success": False, "error": f"Cartesia call failed: {str(e)}"}


def _process_chunk_worker(chunk_tuple):
    index, chunk_text, ref_b64, lang_id, url, is_f5 = chunk_tuple
    payload = {
        "chunk_text": chunk_text,
        "reference_audio_b64": ref_b64
    }
    if not is_f5:
        payload["language_id"] = lang_id

    try:
        r = requests.post(url, json=payload, timeout=_TIMEOUT_SEC)
        if r.status_code == 200:
            res = r.json()
            if res.get("success") and res.get("audio_b64"):
                return (index, True, base64.b64decode(res["audio_b64"]))
            return (index, False, res.get("error", "Empty audio worker response"))
        return (index, False, f"HTTP {r.status_code}")
    except Exception as e:
        return (index, False, str(e))


def generate(text: str, reference_audio_b64: str, language_id: str = "en") -> dict:
    char_count = len(text.strip())

    if char_count < 2000:
        target_url = CHATTERBOX_ENDPOINT_URL
        max_chars = 150
        is_f5 = False
        provider_name = "chatterbox_parallel"
    else:
        target_url = F5TTS_ENDPOINT_URL
        max_chars = 300
        is_f5 = True
        provider_name = "f5tts_parallel"

    if not target_url:
        if CARTESIA_API_KEY:
            return _call_cartesia_fallback(text)
        return {"success": False, "error": f"Target endpoint not configured for provider: {provider_name}"}

    chunks = _split_into_chunks(text, max_chars=max_chars)
    tasks = [(i, chunk, reference_audio_b64, language_id, target_url, is_f5) for i, chunk in enumerate(chunks)]

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        results = list(executor.map(_process_chunk_worker, tasks))

    results.sort(key=lambda x: x[0])

    audio_segments = []
    for index, success, data in results:
        if not success:
            if CARTESIA_API_KEY:
                return _call_cartesia_fallback(text)
            return {"success": False, "error": f"Parallel Chunk {index+1} failed ({data})"}
        audio_segments.append(data)

    combined = AudioSegment.empty()
    for b in audio_segments:
        seg = AudioSegment.from_file(io.BytesIO(b), format="wav")
        combined = combined.append(seg, crossfade=40) if len(combined) > 0 else seg

    out_buf = io.BytesIO()
    combined.export(out_buf, format="wav")
    audio_b64 = base64.b64encode(out_buf.getvalue()).decode("ascii")

    return {"success": True, "audio_b64": audio_b64, "provider": provider_name}
