"""
modal_workers/chatterbox/app.py — Chatterbox-Turbo voice cloning on Modal.

Deployed via `modal deploy` (see .github/workflows/deploy-modal-worker.yml —
runs on GitHub's servers, no local machine needed). Exposes a single HTTP
endpoint that clone_engine.py calls directly.

Simpler than the RunPod version this replaced: RunPod's async /run +
/status polling pattern existed mainly because RunPod's own API nudges you
toward it for GPU jobs. Here we just use a normal synchronous web endpoint —
clone_engine.py already calls this from a background thread (decoupled from
the actual Flask request/response cycle), so blocking on one HTTP call for
up to a few minutes is perfectly fine and much simpler than a job queue.

Same pkuseg workaround as the RunPod Dockerfile: chatterbox-tts's PyPI
package pulls in a Chinese-segmentation dependency (pkuseg) that fails to
compile on most Linux environments — a known upstream bug
(resemble-ai/chatterbox#231/#237/#367). Installing from source with that
one line stripped out avoids it.
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
        # Runs once per container, not once per request — the container
        # stays warm for `scaledown_window` seconds after the last request,
        # so back-to-back generations skip the (slow) model load entirely.
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
        import torchaudio as ta

        text = (req.text or "").strip()
        ref_b64 = req.reference_audio_b64

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

            wav = self.model.generate(text, audio_prompt_path=ref_path)

            buf = io.BytesIO()
            ta.save(buf, wav, self.model.sr, format="wav")
            buf.seek(0)
            audio_b64 = base64.b64encode(buf.read()).decode("ascii")
            return {"audio_b64": audio_b64}
        except Exception as e:
            return {"error": str(e)}
        finally:
            if ref_path and os.path.exists(ref_path):
                os.remove(ref_path)
