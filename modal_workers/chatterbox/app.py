"""
modal_workers/chatterbox/app.py — Chatterbox Multilingual voice cloning on
Modal.

CHANGED (again): switched from ChatterboxTurboTTS (English-only) to
ChatterboxMultilingualTTS (23 languages, incl. Hindi — still MIT licensed,
same license terms as Turbo). VoxCraft's actual audience is mostly Urdu/
Hindi speakers, and Turbo simply couldn't serve them. Urdu itself isn't one
of the 23 supported languages, so Urdu text is transliterated to Devanagari
on the VPS side (urdu_transliteration.py, in the main app repo — a pure
CPU text operation, doesn't belong in a GPU worker) and generated via the
Hindi language_id, since Urdu and Hindi are the same spoken language and
differ only in script.

CHUNKED GENERATION — fixes long-input model collapse.

Root cause of the stuck-samples/duplicate-frames/click artifacts found in
production testing (40s clips): the whole input text was sent through
model.generate() in a single autoregressive pass. Autoregressive TTS models
(Chatterbox included) are trained overwhelmingly on short utterances —
pushed past their comfortable single-pass length, attention drifts and the
model starts repeating a frame verbatim (duplicate frames), freezing
(stuck samples), or cutting to silence early (abrupt truncation). Tuning
temperature/top_p/repetition_penalty (see git history of this file) treats
a symptom of this, not the cause, and doesn't fully fix it.

Fix: split text into sentence-sized chunks (<= MAX_CHUNK_CHARS each),
generate each chunk separately against the same reference voice, then
concatenate with a short crossfade so the seams between chunks aren't
audible as clicks. Each individual generate() call now stays well within
the length the model was actually trained on, which is what actually
prevents the collapse — not the sampling parameters.

Also fixes a mismatch: app.py (the main Flask backend) tells users the cap
is 2000 characters (CLONE_CHAR_LIMIT), but this worker was rejecting
anything over 1000 — a silent contradiction. Raised to match, now that
chunking makes long text safe to generate.
"""

import re
import traceback

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

# Keep in sync with CLONE_CHAR_LIMIT in the main app's app.py.
MAX_TOTAL_CHARS = 2000
# Per-chunk cap — this is the number that actually matters for avoiding
# model collapse. ~200 chars is roughly one or two sentences, well within
# what these models handle reliably in a single generate() call.
MAX_CHUNK_CHARS = 200
CROSSFADE_MS = 40  # short crossfade at chunk seams — long enough to mask a splice, short enough to not smear words


class CloneRequest(BaseModel):
    text: str
    reference_audio_b64: str
    language_id: str = "en"  # "en" or "hi" — see module docstring for how Urdu maps to "hi"


class CloneResponse(BaseModel):
    success: bool
    audio_b64: str = ""
    error: str = ""
    chunks_generated: int = 0
    duration_seconds: float = 0.0


def _split_into_chunks(text: str, max_chars: int) -> list:
    """Splits on sentence boundaries first; any sentence still over
    max_chars gets hard-split on the nearest space so we never cut a word
    in half. Keeps chunks close to natural speech-breath lengths, which is
    also just better prosody than an arbitrary character cutoff."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(sentence) <= max_chars:
            current = sentence
        else:
            # Single sentence longer than the cap — hard-split on spaces.
            words = sentence.split(" ")
            piece = ""
            for word in words:
                candidate = f"{piece} {word}".strip() if piece else word
                if len(candidate) <= max_chars:
                    piece = candidate
                else:
                    if piece:
                        chunks.append(piece)
                    piece = word
            if piece:
                current = piece
    if current:
        chunks.append(current)
    # Filter out any empty chunks
    return [c for c in chunks if c.strip()]


@app.cls(gpu="A10G", timeout=300, scaledown_window=300)
class ChatterboxWorker:
    @modal.enter()
    def load_model(self):
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = ChatterboxMultilingualTTS.from_pretrained(device=device)

    def _generate_chunk(self, text: str, ref_path: str, language_id: str):
        return self.model.generate(
            text,
            audio_prompt_path=ref_path,
            language_id=language_id,
            temperature=0.4,
            top_p=0.8,
            top_k=50,
            repetition_penalty=1.2,
        )

    def _concat_with_crossfade(self, waveforms: list, sr: int):
        """Concatenates a list of 1-D torch tensors with a short
        crossfade at each seam. A hard concatenation (no crossfade) is
        exactly what produces the click/pop artifacts at chunk boundaries
        — two independently-generated waveforms rarely end/start at the
        same phase or amplitude, so the discontinuity reads as a click."""
        import torch
        if not waveforms:
            return None
        fade_samples = int(sr * CROSSFADE_MS / 1000)
        result = waveforms[0]
        for next_wav in waveforms[1:]:
            if result.shape[-1] < fade_samples or next_wav.shape[-1] < fade_samples:
                result = torch.cat([result, next_wav], dim=-1)
                continue
            fade_out = torch.linspace(1.0, 0.0, fade_samples)
            fade_in = torch.linspace(0.0, 1.0, fade_samples)
            tail = result[..., -fade_samples:] * fade_out
            head = next_wav[..., :fade_samples] * fade_in
            crossfaded = tail + head
            result = torch.cat([
                result[..., :-fade_samples],
                crossfaded,
                next_wav[..., fade_samples:],
            ], dim=-1)
        return result

    def _trim_trailing_silence(self, wav, sr: int, threshold: float = 0.01, max_trim_sec: float = 1.0):
        """Trims trailing near-silence beyond a reasonable pad, instead of
        leaving whatever the model happened to emit (which is what
        produced the observed "last 1 second is pure silence, hard cut"
        artifact) — keeps a small natural pad instead of cutting flush.
        max_trim_sec is a CAP on how much gets removed in one go (safety
        net for a pathological case), not a minimum threshold to trigger
        trimming at all."""
        import torch
        max_trim_samples = int(sr * max_trim_sec)
        abs_wav = wav.abs()
        nonsilent = (abs_wav > threshold).nonzero()
        if nonsilent.numel() == 0:
            return wav
        last_sound_idx = int(nonsilent[..., -1].max().item())
        pad = int(sr * 0.15)  # keep a small natural tail instead of cutting flush
        natural_cutoff = min(wav.shape[-1], last_sound_idx + pad)
        min_allowed_cutoff = max(natural_cutoff, wav.shape[-1] - max_trim_samples)
        return wav[..., :min_allowed_cutoff]

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
        language_id = req.language_id if req.language_id in ("en", "hi") else "en"

        # ── Validation ──────────────────────────────────────────────────
        if not text:
            return CloneResponse(success=False, error="No text provided.").model_dump()
        if not ref_b64:
            return CloneResponse(success=False, error="No reference_audio_b64 provided.").model_dump()
        if len(text) > MAX_TOTAL_CHARS:
            return CloneResponse(
                success=False,
                error=f"Text too long ({len(text)} chars, max {MAX_TOTAL_CHARS})."
            ).model_dump()

        tmp_path = None
        ref_path = None
        try:
            # ── Decode reference audio ─────────────────────────────────
            try:
                ref_bytes = base64.b64decode(ref_b64)
            except Exception:
                return CloneResponse(success=False, error="Invalid base64 in reference_audio_b64.").model_dump()

            if len(ref_bytes) == 0:
                return CloneResponse(success=False, error="Reference audio is empty.").model_dump()

            with tempfile.NamedTemporaryFile(suffix=".upload", delete=False) as f:
                f.write(ref_bytes)
                tmp_path = f.name

            # ── Load and validate reference ────────────────────────────
            try:
                waveform, sr = ta.load(tmp_path)
            except Exception as e:
                return CloneResponse(success=False, error=f"Cannot load reference audio: {e}").model_dump()

            duration = waveform.shape[1] / sr

            if duration < 3:
                return CloneResponse(
                    success=False,
                    error=f"Reference too short ({duration:.1f}s). Use 5-15s."
                ).model_dump()
            if duration > 30:
                return CloneResponse(
                    success=False,
                    error=f"Reference too long ({duration:.1f}s). Use 5-15s."
                ).model_dump()

            # ── Preprocess reference ───────────────────────────────────
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

            # ── Chunk and generate ─────────────────────────────────────
            chunks = _split_into_chunks(text, MAX_CHUNK_CHARS)
            if not chunks:
                return CloneResponse(success=False, error="Text produced no valid chunks after splitting.").model_dump()

            waveforms = []
            for i, chunk_text in enumerate(chunks):
                try:
                    wav = self._generate_chunk(chunk_text, ref_path, language_id)
                except Exception as e:
                    return CloneResponse(
                        success=False,
                        error=f"Chunk {i+1}/{len(chunks)} failed: {e}"
                    ).model_dump()

                if not isinstance(wav, torch.Tensor):
                    wav = torch.tensor(wav)
                while wav.dim() > 2:
                    wav = wav.squeeze(0)
                if wav.dim() == 1:
                    wav = wav.unsqueeze(0)
                elif wav.dim() == 2 and wav.shape[0] > 2:
                    wav = wav[0:1, :]
                waveforms.append(wav)

            # ── Concatenate and post-process ───────────────────────────
            if len(waveforms) == 1:
                wav = waveforms[0]
            else:
                wav = self._concat_with_crossfade(waveforms, self.model.sr)

            if wav is None:
                return CloneResponse(success=False, error="Audio generation produced no output.").model_dump()

            wav = self._trim_trailing_silence(wav, self.model.sr)
            wav = torch.clamp(wav, -1.0, 1.0)

            # ── Encode response ────────────────────────────────────────
            buf = io.BytesIO()
            ta.save(buf, wav, self.model.sr, format="wav")
            buf.seek(0)
            audio_b64 = base64.b64encode(buf.read()).decode("ascii")

            duration_sec = wav.shape[-1] / self.model.sr

            return CloneResponse(
                success=True,
                audio_b64=audio_b64,
                chunks_generated=len(chunks),
                duration_seconds=round(duration_sec, 2)
            ).model_dump()

        except Exception as exc:
            tb = traceback.format_exc()
            return CloneResponse(
                success=False,
                error=f"{exc}\n\n{tb}"
            ).model_dump()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            if ref_path and os.path.exists(ref_path):
                os.remove(ref_path)
