"""
modal_workers/chatterbox/app.py — Chatterbox Multilingual voice cloning on Modal.
Includes automated FFmpeg audio preprocessing/denoising on incoming reference audio.
"""

import os
import re
import subprocess
import traceback

import modal
from pydantic import BaseModel

image = (
    modal.Image.from_registry("nvidia/cuda:12.1.0-devel-ubuntu22.04", add_python="3.11")
    .apt_install("git", "ffmpeg")
    .pip_install("torch==2.4.0", "torchaudio==2.4.0", "numpy", "fastapi[standard]")
    .run_commands(
        "rm -rf \~/.cache/huggingface/hub/models--ResembleAI--chatterbox* || true",
        "git clone --depth 1 https://github.com/resemble-ai/chatterbox.git /opt/chatterbox",
        "cd /opt/chatterbox && sed -i '/pkuseg/d' pyproject.toml && pip install --no-cache-dir -e .",
    )
)

app = modal.App("voxcraft-clone-worker", image=image)

MAX_TOTAL_CHARS = 1400
MAX_CHUNK_CHARS = 150
CROSSFADE_MS = 40


class CloneRequest(BaseModel):
    text: str
    reference_audio_b64: str
    language_id: str = "en"


class CloneResponse(BaseModel):
    success: bool
    audio_b64: str = ""
    error: str = ""
    chunks_generated: int = 0
    duration_seconds: float = 0.0


def preprocess_reference_audio(input_path: str, output_path: str, sample_rate: int = 24000) -> bool:
    """Cleans reference audio using FFmpeg prior to TTS inference.
    Applies high-pass filtering (80Hz), FFT denoising, silence trimming, and loudness norm."""
    filter_chain = (
        "highpass=f=80,"
        "afftdn=nr=10:nf=-30,"
        "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB,"
        "areverse,silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB,areverse,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", filter_chain,
        "-ar", str(sample_rate),
        "-ac", "1",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        return False


def _split_into_chunks(text: str, max_chars: int) -> list:
    """Splits on sentence boundaries (including Urdu/Arabic/Devanagari stops)."""
    sentences = re.split(r"(?<=[.!?۔؟।])\s+", text.strip())
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
    return [c for c in chunks if c.strip()]


@app.cls(gpu="A10G", timeout=600, scaledown_window=300)
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
            temperature=0.20,          # commercial: very stable, minimal hallucination
            top_p=0.72,
            repetition_penalty=1.35,
            min_p=0.05,
            cfg_weight=0.0,
            exaggeration=0.38,         # controlled expressiveness
        )

    def _cap_runaway_generation(self, wav, chunk_text: str, sr: int):
        min_duration_sec = 1.6
        chars = max(len(chunk_text.strip()), 1)
        expected_sec = chars / 10.0
        max_duration_sec = max(min_duration_sec, expected_sec * 2.4)
        max_samples = int(max_duration_sec * sr)
        if wav.shape[-1] > max_samples:
            wav = wav[..., :max_samples]
        return wav

    def _concat_with_crossfade(self, waveforms: list, sr: int):
        import torch
        if not waveforms:
            return None
        fade_samples = int(sr * CROSSFADE_MS / 1000)
        result = waveforms[0]
        for next_wav in waveforms[1:]:
            if result.shape[-1] < fade_samples or next_wav.shape[-1] < fade_samples:
                result = torch.cat([result, next_wav], dim=-1)
                continue
            fade_out = torch.linspace(1.0, 0.0, fade_samples, device=result.device, dtype=result.dtype)
            fade_in = torch.linspace(0.0, 1.0, fade_samples, device=result.device, dtype=result.dtype)
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
        import torch
        max_trim_samples = int(sr * max_trim_sec)
        abs_wav = wav.abs()
        nonsilent = (abs_wav > threshold).nonzero()
        if nonsilent.numel() == 0:
            return wav
        last_sound_idx = int(nonsilent[..., -1].max().item())
        pad = int(sr * 0.15)
        natural_cutoff = min(wav.shape[-1], last_sound_idx + pad)
        min_allowed_cutoff = max(natural_cutoff, wav.shape[-1] - max_trim_samples)
        return wav[..., :min_allowed_cutoff]

    @modal.fastapi_endpoint(method="POST")
    def generate(self, req: CloneRequest):
        import base64
        import io
        import tempfile

        import torch
        import torchaudio as ta

        text = (req.text or "").strip()
        ref_b64 = req.reference_audio_b64
        language_id = req.language_id if req.language_id in ("en", "hi") else "en"

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
            try:
                ref_bytes = base64.b64decode(ref_b64)
            except Exception:
                return CloneResponse(success=False, error="Invalid base64 in reference_audio_b64.").model_dump()

            if len(ref_bytes) == 0:
                return CloneResponse(success=False, error="Reference audio is empty.").model_dump()

            with tempfile.NamedTemporaryFile(suffix=".upload", delete=False) as f:
                f.write(ref_bytes)
                tmp_path = f.name

            # ── Clean & Denoise Reference Audio via FFmpeg ──────────────
            clean_tmp_path = tmp_path + "_clean.wav"
            if preprocess_reference_audio(tmp_path, clean_tmp_path, sample_rate=self.model.sr):
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                tmp_path = clean_tmp_path

            # ── Load and validate reference ────────────────────────────
            try:
                waveform, sr = ta.load(tmp_path)
            except Exception as e:
                return CloneResponse(success=False, error=f"Cannot load reference audio: {e}").model_dump()

            duration = waveform.shape[1] / sr
            if duration < 3:
                return CloneResponse(
                    success=False,
                    error=f"Reference too short ({duration:.1f}s). Minimum required is 3 seconds."
                ).model_dump()

            if duration > 10:
                max_samples = int(10 * sr)
                waveform = waveform[:, :max_samples]

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
                return CloneResponse(success=False, error="Text produced no valid chunks.").model_dump()

            waveforms = []
            for i, chunk_text in enumerate(chunks):
                wav = None
                last_error = None
                # Commercial: try up to 2 times if chunk is mostly silent / too short
                for attempt in range(2):
                    try:
                        candidate = self._generate_chunk(chunk_text, ref_path, language_id)
                    except Exception as e:
                        last_error = e
                        continue

                    if not isinstance(candidate, torch.Tensor):
                        candidate = torch.tensor(candidate)
                    while candidate.dim() > 2:
                        candidate = candidate.squeeze(0)
                    if candidate.dim() == 1:
                        candidate = candidate.unsqueeze(0)
                    elif candidate.dim() == 2 and candidate.shape[0] > 2:
                        candidate = candidate[0:1, :]

                    candidate = self._cap_runaway_generation(candidate, chunk_text, self.model.sr)

                    # Quality gate: reject near-silent or extremely short chunks
                    duration = candidate.shape[-1] / self.model.sr
                    energy = float(candidate.abs().mean())
                    min_expected = max(1.2, len(chunk_text.strip()) / 14.0)

                    if duration >= min_expected * 0.55 and energy > 0.006:
                        wav = candidate
                        break
                    # otherwise retry once

                if wav is None:
                    return CloneResponse(
                        success=False,
                        error=f"Chunk {i+1}/{len(chunks)} failed after retries: {last_error or 'low quality / silent output'}"
                    ).model_dump()

                waveforms.append(wav)

            if len(waveforms) == 1:
                wav = waveforms[0]
            else:
                wav = self._concat_with_crossfade(waveforms, self.model.sr)

            if wav is None:
                return CloneResponse(success=False, error="Audio generation produced no output.").model_dump()

            wav = self._trim_trailing_silence(wav, self.model.sr)
            wav = torch.clamp(wav, -1.0, 1.0)

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