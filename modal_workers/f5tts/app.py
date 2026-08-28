import base64
import io
import os
import tempfile
import modal
from pydantic import BaseModel

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg")
    .pip_install(
        "torch==2.3.1",
        "torchaudio==2.3.1",
        "f5-tts",
        "pydub",
        "soundfile",
        "numpy",
        "fastapi[standard]"
    )
)

app = modal.App("voxcraft-f5tts-worker", image=image)

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
        self.model = F5TTS(model="F5TTS_Base", device=device)

    @modal.fastapi_endpoint(method="POST")
    def generate(self, req: SingleChunkRequest):
        """Generates audio for a SINGLE text chunk to enable parallel execution across GPUs."""
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
                os.remove(tmp_ref_path)
