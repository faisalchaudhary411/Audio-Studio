"""
modal_workers/chatterbox/app.py — Chatterbox-Turbo voice cloning on Modal.

FIXED v3:
1. Added "success" key to all responses.
2. Fixed wav tensor shape handling.
3. Added amplitude clamping.
4. Added text length guard.
5. Added audio format normalization (any format → 24kHz mono WAV).
6. CRITICAL FIX: Set generation parameters to near-deterministic mode.
   Default temperature=0.8, top_p=0.95, top_k=1000 caused the model to
   hallucinate random text instead of speaking the provided input. The
   output contained system memory fragments ("SECRET_KEY", "SQLite",
   etc.) because the model was in creative/continuation mode rather
   than strict TTS mode.
7. FIXED sample rate: model generates at 44100 Hz, but we were saving
   at 24000 Hz. Now correctly uses model.sr (44100) for output.
"""

import modal
from pydantic import BaseModel

image = (
    modal.Image.from_registry("nvidia/cuda:12.1.0-devel-ubuntu22.04", add_python="3.11")
    .apt_install("git")
    .pip_install("torch==2.4.0", "torchaudio==2.4.0", "numpy", "fastapi[standard]")
    .run_commands(
        "git clone --depth 1 https://github.com/resemble-ai/chatterbox.git /opt/chatterbox",
        "cd /opt/chatterbox && sed -i '/pkuseg/d' pyproject.toml && pip install --no-cache-dir -e .",
    )
)

app = modal.App("voxcraft-clone-worker", image=image)


class CloneRequest(BaseModel):
    text: str
    reference_audio_b64: str


@app.cls(gpu="A10G", timeout=300, scaledown_window=300)
class ChatterboxWorker:
    @modal.enter()
    def load_model(self):
        import torch
        from chatterbox.tts_turbo import ChatterboxTurboTTS
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = ChatterboxTurboTTS.from_pretrained(device=device)
        print(f"[INIT] Model loaded. Sample rate: {self.model.sr} Hz")

    @modal.fastapi_endpoint(method="POST")
    def generate(self, req: CloneRequest):
        import base64
        import io
        import os
        import tempfile

        import torch
        import torchaudio as ta

        text = (req.text or "").strip()
        ref_b64 = req.reference_audio_b64

        print(f"[DEBUG] Received text: {repr(text[:100])}")
        print(f"[DEBUG] Text length: {len(text)}")
        print(f"[DEBUG] Ref b64 length: {len(ref_b64 or '')}")

        if not text:
            return {"success": False, "error": "No text provided."}
        if not ref_b64:
            return {"success": False, "error": "No reference_audio_b64 provided."}
        if len(text) > 1000:
            return {"success": False, "error": "Text too long (max 1000 chars)."}

        tmp_path = None
        ref_path = None
        try:
            ref_bytes = base64.b64decode(ref_b64)

            # Normalize ANY audio format to clean mono WAV
            with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
                f.write(ref_bytes)
                tmp_path = f.name

            waveform, sr = ta.load(tmp_path)

            # Convert to mono
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)

            # Chatterbox-Turbo expects reference at its native sample rate
            # (model will resample internally, but let's be clean)
            if sr != self.model.sr:
                resampler = ta.transforms.Resample(sr, self.model.sr)
                waveform = resampler(waveform)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                ref_path = f.name
            ta.save(ref_path, waveform, self.model.sr, format="wav")

            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                tmp_path = None

            # --- CRITICAL FIX: Near-deterministic generation ---
            # Default params (temp=0.8, top_p=0.95, top_k=1000) cause
            # hallucination/continuation instead of strict TTS.
            wav = self.model.generate(
                text,
                audio_prompt_path=ref_path,
                temperature=0.1,        # Very low randomness
                top_p=0.1,              # Very restrictive sampling
                top_k=10,               # Narrow token selection
                repetition_penalty=1.0, # No penalty (can cause skips)
            )

            # Normalize tensor shape
            if not isinstance(wav, torch.Tensor):
                wav = torch.tensor(wav)

            while wav.dim() > 2:
                wav = wav.squeeze(0)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            elif wav.dim() == 2 and wav.shape[0] > 2:
                wav = wav[0:1, :]

            wav = torch.clamp(wav, -1.0, 1.0)

            # Save at MODEL sample rate (44100 Hz), not 24000
            buf = io.BytesIO()
            ta.save(buf, wav, self.model.sr, format="wav")
            buf.seek(0)
            audio_b64 = base64.b64encode(buf.read()).decode("ascii")

            print(f"[DEBUG] Generated audio length: {len(audio_b64)} chars b64")
            return {"success": True, "audio_b64": audio_b64}

        except Exception as exc:
            print(f"[ERROR] {exc}")
            return {"success": False, "error": str(exc)}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            if ref_path and os.path.exists(ref_path):
                os.remove(ref_path)
