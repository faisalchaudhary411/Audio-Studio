"""
handler.py — RunPod serverless worker for voice cloning via Chatterbox-Turbo
(Resemble AI, MIT license — see clone_engine.py in the main app for why this
model was chosen over XTTS-v2/F5-TTS).

RunPod serverless workers are just a Python process with one entry point:
`runpod.serverless.start({"handler": handler})`. RunPod calls `handler(event)`
once per job; `event["input"]` is whatever JSON the caller submitted to
POST /run. The model loads once at container start (cold start) and stays
warm for however many jobs the container is kept alive for — that's why
model loading happens at module level, not inside handler().

Expected input:
  {
    "text": "text to speak in the cloned voice",
    "reference_audio_b64": "<base64-encoded wav/mp3/m4a/ogg reference clip>"
  }

Returns:
  {"audio_b64": "<base64-encoded wav>"}
  or {"error": "..."} on failure — RunPod surfaces this as the job's output,
  the polling client in clone_engine.py checks for this key.
"""

import base64
import io
import os
import tempfile

import runpod
import torch
import torchaudio as ta
from chatterbox.tts_turbo import ChatterboxTurboTTS

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"[chatterbox-worker] Loading model on {DEVICE}...")
_model = ChatterboxTurboTTS.from_pretrained(device=DEVICE)
print("[chatterbox-worker] Model loaded, ready for jobs.")


def handler(event):
    job_input = event.get("input") or {}
    text = (job_input.get("text") or "").strip()
    ref_b64 = job_input.get("reference_audio_b64")

    if not text:
        return {"error": "No text provided."}
    if not ref_b64:
        return {"error": "No reference_audio_b64 provided."}

    ref_path = None
    try:
        ref_bytes = base64.b64decode(ref_b64)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(ref_bytes)
            ref_path = f.name

        wav = _model.generate(text, audio_prompt_path=ref_path)

        buf = io.BytesIO()
        ta.save(buf, wav, _model.sr, format="wav")
        buf.seek(0)
        audio_b64 = base64.b64encode(buf.read()).decode("ascii")
        return {"audio_b64": audio_b64}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if ref_path and os.path.exists(ref_path):
            os.remove(ref_path)


runpod.serverless.start({"handler": handler})
