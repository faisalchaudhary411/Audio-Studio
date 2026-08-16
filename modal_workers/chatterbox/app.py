"""
modal_workers/chatterbox/app.py — Chatterbox-Turbo voice cloning on Modal.

Deployed via `modal deploy` (see .github/workflows/deploy-modal-worker.yml).
Exposes a single synchronous HTTP endpoint that clone_engine.py calls directly.

FIXED:
1. Added "success" key to all responses so clone_engine.py can distinguish
   success from error properly.
2. Fixed wav tensor shape handling — Chatterbox returns variable shapes
   depending on text length, which torchaudio.save() was corrupting.
3. Added amplitude clamping to prevent clipping/distortion.
4. Added text length guard — very long text causes quality degradation.
5. Added audio format normalization — converts ANY uploaded format (MP3,
   M4A, OGG, WAV) to clean 24kHz mono WAV before feeding to model.
   Previously MP3 bytes were written to a .wav file which could confuse
   the model or torchaudio.

Same pkuseg workaround as before (upstream bug resemble-ai/chatterbox#231).
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

            # --- FIX: Normalize ANY audio format to clean 24kHz mono WAV ---
            # Write raw bytes to temp file (any extension, torchaudio detects)
            with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
                f.write(ref_bytes)
                tmp_path = f.name

            # Load with torchaudio (auto-detects MP3, M4A, OGG, WAV, etc.)
            waveform, sr = ta.load(tmp_path)

            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)

            # Resample to model's sample rate if needed
            if sr != self.model.sr:
                resampler = ta.transforms.Resample(sr, self.model.sr)
                waveform = resampler(waveform)

            # Save as clean WAV for the model
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                ref_path = f.name
            ta.save(ref_path, waveform, self.model.sr, format="wav")

            # Clean up the raw temp file
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                tmp_path = None

            # Generate audio
            wav = self.model.generate(text, audio_prompt_path=ref_path)

            # --- FIX: Normalize tensor shape for torchaudio.save ---
            if not isinstance(wav, torch.Tensor):
                wav = torch.tensor(wav)

            # Squeeze out any extra dimensions, ensure (channels, samples)
            while wav.dim() > 2:
                wav = wav.squeeze(0)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)  # (samples,) → (1, samples)
            elif wav.dim() == 2 and wav.shape[0] > 2:
                # Probably (batch, samples) — keep first output only
                wav = wav[0:1, :]

            # Clamp to prevent clipping / distortion
            wav = torch.clamp(wav, -1.0, 1.0)

            # Save to WAV buffer
            buf = io.BytesIO()
            ta.save(buf, wav, self.model.sr, format="wav")
            buf.seek(0)
            audio_b64 = base64.b64encode(buf.read()).decode("ascii")

            return {"success": True, "audio_b64": audio_b64}

        except Exception as exc:
            return {"success": False, "error": str(exc)}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            if ref_path and os.path.exists(ref_path):
                os.remove(ref_path)
