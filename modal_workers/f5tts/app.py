"""
modal_workers/f5tts/app.py — VoxCraft F5-TTS Modal GPU worker.

IMPORTANT LICENSE NOTE: this worker intentionally does NOT load the
official SWivid/F5-TTS English/Mandarin checkpoint — that checkpoint is
CC-BY-NC-4.0 (non-commercial) due to its Emilia training data, which
VoxCraft (a paid product) cannot legally use. Instead this loads the
SPRINGLab/F5-Hindi-24KHz checkpoint, which is CC-BY-4.0 (commercial use
permitted, attribution required) — see
https://huggingface.co/SPRINGLab/F5-Hindi-24KHz

Consequence: this worker is Hindi/Urdu-only. English text sent here will
produce garbled output since the checkpoint's vocab is Devanagari-based —
routing must never send plain English requests to this endpoint (enforced
in modal_client.py, not here).

Urdu text should arrive already transliterated to Devanagari (same
urdu_transliteration.py conversion clone_engine.py already applies for
the Chatterbox path) — Urdu and Hindi are the same spoken language, only
the script differs.
"""
import base64
import io
import os
import tempfile
import modal
from pydantic import BaseModel

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg", "build-essential", "python3-dev")
    .pip_install(
        "torch==2.3.1",
        "torchaudio==2.3.1",
        "soundfile",
        "numpy",
        "pydub",
        "fastapi[standard]"
    )
    .pip_install("f5-tts")
)

app = modal.App("voxcraft-f5tts-worker", image=image)

# Verified against F5-TTS's own community-checkpoint registry
# (SWivid/F5-TTS src/f5_tts/infer/SHARED.md, "Hindi" section) — do not
# guess these numbers if swapping checkpoints later; a mismatched config
# fails to load the state dict instead of just sounding wrong.
HINDI_CKPT = "hf://SPRINGLab/F5-Hindi-24KHz/model_2500000.safetensors"
HINDI_VOCAB = "hf://SPRINGLab/F5-Hindi-24KHz/vocab.txt"
HINDI_MODEL_CFG = dict(dim=768, depth=18, heads=12, ff_mult=2, text_dim=512, conv_layers=4, pe_attn_head=1)

class SingleChunkRequest(BaseModel):
    chunk_text: str
    reference_audio_b64: str
    ref_text: str = ""

class LongCloneResponse(BaseModel):
    success: bool
    audio_b64: str = ""
    error: str = ""

@app.cls(gpu="A10G", timeout=600, scaledown_window=300)
class F5TTSWorker:
    @modal.enter()
    def load_model(self):
        import torch
        from f5_tts.api import F5TTS
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = F5TTS(
            model="F5TTS_v1_Base",  # ignored for architecture once ckpt_file/vocab_file/model_cfg are set below — kept only as a valid preset name the constructor expects
            ckpt_file=HINDI_CKPT,
            vocab_file=HINDI_VOCAB,
            model_cfg=HINDI_MODEL_CFG,
            device=device,
        )

    @modal.fastapi_endpoint(method="POST")
    def generate(self, req: SingleChunkRequest):
        import soundfile as sf

        chunk_text = (req.chunk_text or "").strip()
        ref_b64 = req.reference_audio_b64

        if not chunk_text or not ref_b64:
            return LongCloneResponse(success=False, error="Missing chunk text or reference audio.").model_dump()

        tmp_ref_path = None
        try:
            ref_bytes = base64.b64decode(ref_b64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(ref_bytes)
                tmp_ref_path = f.name

            wav_out, sr = self.model.infer(
                ref_file=tmp_ref_path,
                ref_text=req.ref_text,
                gen_text=chunk_text,
            )

            buf = io.BytesIO()
            sf.write(buf, wav_out, sr, format="WAV")
            audio_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            return LongCloneResponse(success=True, audio_b64=audio_b64).model_dump()

        except Exception as exc:
            return LongCloneResponse(success=False, error=str(exc)).model_dump()
        finally:
            if tmp_ref_path and os.path.exists(tmp_ref_path):
                try:
                    os.remove(tmp_ref_path)
                except Exception:
                    pass
