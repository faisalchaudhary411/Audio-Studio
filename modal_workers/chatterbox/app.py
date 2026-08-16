"""
modal_workers/chatterbox/app.py — Chatterbox-Turbo voice cloning on Modal.

DIAGNOSTIC VERSION — includes checks to identify why the model generates
system-memory garbage instead of the input text. Run this once, check logs,
then switch back to the clean version once the issue is found.

DIAGNOSTIC CHECKS:
1. Model class verification (ensures ChatterboxTurboTTS loaded, not something else)
2. Test generation WITHOUT reference audio (isolates model vs. reference issue)
3. Reference audio validation (sample rate, duration, amplitude check)
4. Per-request debug logging (text received, output shape, sample stats)

FIXES APPLIED:
- "success" key in all responses
- Near-deterministic generation params (temp=0.1, top_p=0.1, top_k=10)
- Audio format normalization (any format → model.sr mono WAV)
- Tensor shape fix + amplitude clamping
- Text length guard
"""

import modal
from pydantic import BaseModel

image = (
    modal.Image.from_registry("nvidia/cuda:12.1.0-devel-ubuntu22.04", add_python="3.11")
    .apt_install("git", "ffmpeg")
    .pip_install("torch==2.4.0", "torchaudio==2.4.0", "numpy", "fastapi[standard]")
    .run_commands(
        # Clean any stale model cache before install
        "rm -rf ~/.cache/huggingface/hub/models--ResembleAI--chatterbox* || true",
        "git clone --depth 1 https://github.com/resemble-ai/chatterbox.git /opt/chatterbox",
        "cd /opt/chatterbox && sed -i '/pkuseg/d' pyproject.toml && pip install --no-cache-dir -e .",
    )
)

app = modal.App("voxcraft-clone-worker-diag", image=image)


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
        print(f"[DIAG] Loading model on device: {device}")

        self.model = ChatterboxTurboTTS.from_pretrained(device=device)

        # --- DIAGNOSTIC 1: Verify model class ---
        print(f"[DIAG] Model class: {self.model.__class__.__name__}")
        print(f"[DIAG] Model module: {self.model.__class__.__module__}")
        print(f"[DIAG] Sample rate: {self.model.sr}")
        print(f"[DIAG] Total parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        print(f"[DIAG] Device: {next(self.model.parameters()).device}")

        # --- DIAGNOSTIC 2: Test generation WITHOUT reference audio ---
        print(f"[DIAG] Running test generation (no reference)...")
        try:
            test_wav = self.model.generate(
                "Hello world, this is a test.",
                temperature=0.1,
                top_p=0.1,
                top_k=10,
            )
            print(f"[DIAG] Test output shape: {test_wav.shape}")
            print(f"[DIAG] Test output dtype: {test_wav.dtype}")
            print(f"[DIAG] Test output range: [{test_wav.min():.4f}, {test_wav.max():.4f}]")
            print(f"[DIAG] Test output mean: {test_wav.mean():.4f}")

            # Check if output is all zeros or near-zeros (dead model)
            if test_wav.abs().max() < 0.001:
                print(f"[DIAG] ⚠️ WARNING: Test output is essentially silent!")
            else:
                print(f"[DIAG] ✅ Test output has audible content")

            # Check for NaN/Inf
            if torch.isnan(test_wav).any():
                print(f"[DIAG] ⚠️ WARNING: Test output contains NaN!")
            if torch.isinf(test_wav).any():
                print(f"[DIAG] ⚠️ WARNING: Test output contains Inf!")

        except Exception as e:
            print(f"[DIAG] ❌ Test generation FAILED: {e}")

        print(f"[DIAG] Model ready.")

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

        print(f"[REQ] Received text ({len(text)} chars): {repr(text[:120])}")
        print(f"[REQ] Ref b64 length: {len(ref_b64 or '')}")

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
            print(f"[REQ] Decoded ref audio: {len(ref_bytes)} bytes")

            # Save raw bytes
            with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
                f.write(ref_bytes)
                tmp_path = f.name

            # Load and inspect reference audio
            waveform, sr = ta.load(tmp_path)
            print(f"[REQ] Ref audio loaded: shape={waveform.shape}, sr={sr}, "
                  f"duration={waveform.shape[1]/sr:.2f}s, "
                  f"channels={waveform.shape[0]}, "
                  f"range=[{waveform.min():.4f}, {waveform.max():.4f}]")

            # Convert to mono
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)
                print(f"[REQ] Converted to mono")

            # Resample to model rate
            if sr != self.model.sr:
                print(f"[REQ] Resampling {sr} → {self.model.sr}")
                resampler = ta.transforms.Resample(sr, self.model.sr)
                waveform = resampler(waveform)

            # Save clean WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                ref_path = f.name
            ta.save(ref_path, waveform, self.model.sr, format="wav")
            print(f"[REQ] Saved clean ref to: {ref_path}")

            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
                tmp_path = None

            # Generate with locked-down params
            print(f"[REQ] Starting generation...")
            wav = self.model.generate(
                text,
                audio_prompt_path=ref_path,
                temperature=0.1,
                top_p=0.1,
                top_k=10,
                repetition_penalty=1.0,
            )
            print(f"[REQ] Raw output: shape={wav.shape}, dtype={wav.dtype}")

            # Normalize shape
            if not isinstance(wav, torch.Tensor):
                wav = torch.tensor(wav)
            while wav.dim() > 2:
                wav = wav.squeeze(0)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            elif wav.dim() == 2 and wav.shape[0] > 2:
                wav = wav[0:1, :]

            wav = torch.clamp(wav, -1.0, 1.0)
            print(f"[REQ] Final output: shape={wav.shape}, "
                  f"range=[{wav.min():.4f}, {wav.max():.4f}]")

            # Encode
            buf = io.BytesIO()
            ta.save(buf, wav, self.model.sr, format="wav")
            buf.seek(0)
            audio_b64 = base64.b64encode(buf.read()).decode("ascii")
            print(f"[REQ] Encoded: {len(audio_b64)} chars b64")

            return {"success": True, "audio_b64": audio_b64}

        except Exception as exc:
            print(f"[REQ] ❌ ERROR: {exc}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(exc)}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            if ref_path and os.path.exists(ref_path):
                os.remove(ref_path)
