"""
modal_workers/chatterbox/app.py — Chatterbox-Turbo voice cloning on Modal.

FINAL STABLE VERSION — based on diagnostic findings:
- Model: ChatterboxTurboTTS, SR=24000 Hz (confirmed correct)
- Test generation WITHOUT reference works fine
- Problem: reference audio + low temperature causes repetition loops
- Fix: balanced temperature (0.4), moderate top_p/top_k, default repetition_penalty
- Also testing norm_loudness=False to rule out normalization corruption
"""

import modal
from pydantic import BaseModel

image = (
    modal.Image.from_registry("nvidia/cuda:12.1.0-devel-ubuntu22.04", add_python="3.11")
    .apt_install("git", "ffmpeg")
    .pip_install("torch==2.4.0", "torchaudio==2.4.0", "numpy", "fastapi[standard]")
    .run_commands(
        "rm -rf ~/.cache/huggingface/hub/models--ResembleAI--chatterbox* || true",
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

            with tempfile.NamedTemporaryFile(suffix=".upload", delete=False) as f:
                f.write(ref_bytes)
                tmp_path = f.name

            waveform, sr = ta.load(tmp_path)
            duration = waveform.shape[1] / sr

            if duration < 3:
                return {"success": False, "error": f"Reference too short ({duration:.1f}s). Use 5-15s."}
            if duration > 30:
                return {"success": False, "error": f"Reference too long ({duration:.1f}s). Use 5-15s."}

            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)

            if sr != self.model.sr:
                resampler = ta.transforms.Resample(sr, self.model.sr)
                waveform = resampler(waveform)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                ref_path = f.name
            ta.save(ref_path, waveform, self.model.sr, format="wav")

            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                tmp_path = None

            # --- BALANCED PARAMS: not too random, not too deterministic ---
            wav = self.model.generate(
                text,
                audio_prompt_path=ref_path,
                temperature=0.4,
                top_p=0.8,
                top_k=50,
                repetition_penalty=1.2,
                norm_loudness=False,
            )

            if not isinstance(wav, torch.Tensor):
                wav = torch.tensor(wav)
            while wav.dim() > 2:
                wav = wav.squeeze(0)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            elif wav.dim() == 2 and wav.shape[0] > 2:
                wav = wav[0:1, :]

            wav = torch.clamp(wav, -1.0, 1.0)

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
