"""
modal_workers/whisper/app.py — VoxCraft Whisper (faster-whisper) Modal GPU worker.

Speech-to-text on GPU so the VPS stays light (no ~140MB+ model load / OOM risk).
Uses faster-whisper (CTranslate2) for 4–6× speed vs openai-whisper at similar quality.

API (POST JSON):
  {
    "audio_b64": "<base64-encoded audio bytes>",
    "language": "en" | "hi" | "ur" | ... | null,   # null = auto-detect
    "task": "transcribe" | "translate",            # translate → English
    "model_size": "tiny" | "base" | "small" | "medium" | "large-v3" | "turbo",
    "word_timestamps": false,
    "vad_filter": true
  }

Response:
  {
    "success": true,
    "text": "...",
    "language": "en",
    "language_probability": 0.98,
    "duration_sec": 12.4,
    "segments": [ {"start": 0.0, "end": 2.1, "text": "..."}, ... ],
    "srt": "1\\n00:00:00,000 --> ...\\n...",
    "method": "faster-whisper (large-v3)",
    "error": ""
  }

Deploy:
  modal deploy modal_workers/whisper/app.py
  (or via .github/workflows/deploy-modal-whisper-worker.yml)

After deploy, set on VPS:
  MODAL_WHISPER_ENDPOINT_URL=https://...--voxcraft-whisper-worker-whisperworker-transcribe.modal.run
"""

from __future__ import annotations

import base64
import io
import os
import tempfile
import traceback
from typing import Optional

import modal
from pydantic import BaseModel, Field

# ── Image ────────────────────────────────────────────────────────────────
# faster-whisper + CUDA. A10G has 24GB — large-v3 / turbo fit comfortably in
# float16. We pin a recent faster-whisper that ships CTranslate2 CUDA wheels.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "faster-whisper>=1.0.3",
        "numpy",
        "soundfile",
        "fastapi[standard]",
        "pydantic",
    )
)

app = modal.App("voxcraft-whisper-worker", image=image)

# Default model. "turbo" (large-v3-turbo) is the best speed/quality tradeoff
# for production; "large-v3" is highest accuracy. Override per-request via
# model_size if needed.
DEFAULT_MODEL = os.environ.get("WHISPER_MODEL", "large-v3")
# float16 is the sweet spot on A10G; int8 is faster but slightly lossier.
DEFAULT_COMPUTE = os.environ.get("WHISPER_COMPUTE_TYPE", "float16")

ALLOWED_MODELS = {
    "tiny",
    "base",
    "small",
    "medium",
    "large-v1",
    "large-v2",
    "large-v3",
    "turbo",  # alias for large-v3-turbo in recent faster-whisper
    "distil-large-v3",
}


class TranscribeRequest(BaseModel):
    audio_b64: str
    language: Optional[str] = None  # ISO-639-1 e.g. "en", "hi", "ur"; None = auto
    task: str = "transcribe"  # or "translate"
    model_size: str = DEFAULT_MODEL
    word_timestamps: bool = False
    vad_filter: bool = True
    # Optional initial prompt to bias style / domain (e.g. proper nouns)
    initial_prompt: Optional[str] = None


class SegmentOut(BaseModel):
    start: float
    end: float
    text: str


class TranscribeResponse(BaseModel):
    success: bool
    text: str = ""
    language: str = ""
    language_probability: float = 0.0
    duration_sec: float = 0.0
    segments: list = Field(default_factory=list)
    srt: str = ""
    method: str = ""
    error: str = ""


def _fmt_srt_time(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _segments_to_srt(segments) -> str:
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = float(getattr(seg, "start", 0.0) or 0.0)
        end = float(getattr(seg, "end", start) or start)
        text = (getattr(seg, "text", "") or "").strip()
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


@app.cls(
    gpu="A10G",
    timeout=600,
    scaledown_window=300,
    max_containers=2,
)
@modal.concurrent(max_inputs=1)
class WhisperWorker:
    @modal.enter()
    def load_model(self):
        from faster_whisper import WhisperModel

        # Load the default model at container start so the first request
        # after cold-start is not stuck downloading weights.
        model_name = DEFAULT_MODEL if DEFAULT_MODEL in ALLOWED_MODELS else "large-v3"
        print(f"[WHISPER] Loading model={model_name} compute={DEFAULT_COMPUTE} ...")
        self.model = WhisperModel(
            model_name,
            device="cuda",
            compute_type=DEFAULT_COMPUTE,
        )
        self.loaded_model_name = model_name
        print(f"[WHISPER] Model ready: {model_name}")

    def _ensure_model(self, model_size: str):
        """Swap model if the request asks for a different size (rare)."""
        from faster_whisper import WhisperModel

        name = (model_size or DEFAULT_MODEL).strip().lower()
        if name not in ALLOWED_MODELS:
            name = self.loaded_model_name
        if name == self.loaded_model_name:
            return
        print(f"[WHISPER] Switching model {self.loaded_model_name} → {name}")
        self.model = WhisperModel(name, device="cuda", compute_type=DEFAULT_COMPUTE)
        self.loaded_model_name = name

    @modal.fastapi_endpoint(method="POST")
    def transcribe(self, req: TranscribeRequest):
        import soundfile as sf

        if not req.audio_b64 or not req.audio_b64.strip():
            return TranscribeResponse(
                success=False, error="Missing audio_b64."
            ).model_dump()

        task = (req.task or "transcribe").strip().lower()
        if task not in ("transcribe", "translate"):
            task = "transcribe"

        language = None
        if req.language:
            # Accept both "en" and "en-US" style codes
            language = req.language.strip().lower().split("-")[0] or None
            if language in ("", "auto", "none"):
                language = None

        tmp_path = None
        try:
            try:
                audio_bytes = base64.b64decode(req.audio_b64)
            except Exception:
                return TranscribeResponse(
                    success=False, error="Invalid base64 in audio_b64."
                ).model_dump()

            if len(audio_bytes) < 256:
                return TranscribeResponse(
                    success=False, error="Audio payload too small."
                ).model_dump()

            # Write to a temp file so faster-whisper / ffmpeg can probe format.
            # Suffix .audio lets ffmpeg sniff; we also try as wav via soundfile.
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            self._ensure_model(req.model_size)

            segments_iter, info = self.model.transcribe(
                tmp_path,
                language=language,
                task=task,
                beam_size=5,
                vad_filter=bool(req.vad_filter),
                word_timestamps=bool(req.word_timestamps),
                initial_prompt=req.initial_prompt or None,
            )

            segments = list(segments_iter)
            text = " ".join((s.text or "").strip() for s in segments).strip()
            # Collapse repeated whitespace from segment joins
            text = " ".join(text.split())

            seg_out = [
                {
                    "start": round(float(s.start), 3),
                    "end": round(float(s.end), 3),
                    "text": (s.text or "").strip(),
                }
                for s in segments
                if (s.text or "").strip()
            ]

            srt = _segments_to_srt(segments)
            duration = float(getattr(info, "duration", 0.0) or 0.0)
            if duration <= 0 and seg_out:
                duration = float(seg_out[-1]["end"])

            detected_lang = getattr(info, "language", language or "") or ""
            lang_prob = float(getattr(info, "language_probability", 0.0) or 0.0)

            return TranscribeResponse(
                success=True,
                text=text,
                language=detected_lang,
                language_probability=round(lang_prob, 4),
                duration_sec=round(duration, 2),
                segments=seg_out,
                srt=srt,
                method=f"faster-whisper ({self.loaded_model_name})",
            ).model_dump()

        except Exception as exc:
            print(f"[WHISPER ERROR] {exc}\n{traceback.format_exc()}")
            return TranscribeResponse(
                success=False, error=str(exc)[:500]
            ).model_dump()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
