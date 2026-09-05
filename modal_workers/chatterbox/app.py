"""
modal_workers/chatterbox/app.py — Chatterbox Multilingual Voice Cloning (Parallel Ready)
"""

import base64
import io
import os
import re
import subprocess
import tempfile
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

class SingleChunkRequest(BaseModel):
    chunk_text: str
    reference_audio_b64: str
    language_id: str = "en"
    # When True, the caller (clone_engine.py) already ran this exact
    # reference clip through preprocess_reference_audio() once for the
    # whole job and is sending the cleaned/resampled bytes — skip redoing
    # the ffmpeg denoise/silence-trim/loudnorm pass on every segment call.
    already_processed: bool = False

class CloneResponse(BaseModel):
    success: bool
    audio_b64: str = ""
    error: str = ""

CFG_WEIGHT = float(os.environ.get("CHATTERBOX_CFG_WEIGHT", "0.0"))

def postprocess_output_audio(input_path: str, output_path: str, sample_rate: int = 24000) -> bool:
    filter_chain = (
        "highpass=f=80,"
        "acompressor=threshold=-24dB:ratio=2.5:attack=8:release=180,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", filter_chain, "-ar", str(sample_rate), output_path
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

def preprocess_reference_audio(input_path: str, output_path: str, sample_rate: int = 24000) -> bool:
    filter_chain = (
        "highpass=f=80,afftdn=nr=10:nf=-30,"
        "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB,"
        "areverse,silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB,areverse,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", filter_chain, "-ar", str(sample_rate), "-ac", "1", output_path
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
            text, audio_prompt_path=ref_path, language_id=language_id,
            temperature=0.20, top_p=0.72, repetition_penalty=1.35, min_p=0.05,
            cfg_weight=CFG_WEIGHT, exaggeration=0.38
        )

    def _cap_runaway_generation(self, wav, chunk_text: str, sr: int):
        """
        Prevent truly runaway generations (model loops / hallucinated silence)
        while allowing natural speech length.

        Old formula used chars/8.0 (~480 chars/min) which is unrealistically fast
        and caused legitimate speech to be truncated → muted gaps in the final
        stitched audio. Natural narrative pace is ~600-750 chars/min.
        """
        min_duration_sec = 1.8
        chars = max(len(chunk_text.strip()), 1)
        # ~12 chars/sec ≈ 720 chars/min — realistic for clear narration
        expected_sec = chars / 12.0
        # Allow generous headroom (2.8×) and raise the hard ceiling so 350-char
        # segments are no longer cut mid-sentence.
        max_duration_sec = min(max(min_duration_sec, expected_sec * 2.8), 55.0)
        max_samples = int(max_duration_sec * sr)
        if wav.shape[-1] > max_samples:
            wav = wav[..., :max_samples]
        return wav

    def _trim_trailing_silence(self, wav, sr: int, threshold: float = 0.012, max_trim_sec: float = 0.85):
        """Trim only true trailing silence; keep a little natural breathing room."""
        max_trim_samples = int(sr * max_trim_sec)
        abs_wav = wav.abs()
        nonsilent = (abs_wav > threshold).nonzero()
        if nonsilent.numel() == 0:
            return wav
        last_sound_idx = int(nonsilent[..., -1].max().item())
        pad = int(sr * 0.18)
        natural_cutoff = min(wav.shape[-1], last_sound_idx + pad)
        min_allowed_cutoff = max(natural_cutoff, wav.shape[-1] - max_trim_samples)
        return wav[..., :min_allowed_cutoff]

    @modal.fastapi_endpoint(method="POST")
    def generate(self, req: SingleChunkRequest):
        import torch
        import torchaudio as ta

        text = (req.chunk_text or "").strip()
        ref_b64 = req.reference_audio_b64
        language_id = req.language_id if req.language_id in ("en", "hi") else "en"
        already_processed = bool(req.already_processed)

        if not text or not ref_b64:
            return CloneResponse(success=False, error="Missing parameters.").model_dump()

        tmp_path = ref_path = raw_out_path = tmp_path_out = None
        try:
            try:
                ref_bytes = base64.b64decode(ref_b64)
            except Exception:
                return CloneResponse(success=False, error="Invalid base64 in audio.").model_dump()

            with tempfile.NamedTemporaryFile(suffix=".upload", delete=False) as f:
                f.write(ref_bytes)
                tmp_path = f.name

            if not already_processed:
                clean_tmp_path = tmp_path + "_clean.wav"
                if preprocess_reference_audio(tmp_path, clean_tmp_path, sample_rate=self.model.sr):
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    tmp_path = clean_tmp_path

            waveform, sr = ta.load(tmp_path)
            if sr != self.model.sr:
                resampler = ta.transforms.Resample(sr, self.model.sr)
                waveform = resampler(waveform)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                ref_path = f.name
            ta.save(ref_path, waveform, self.model.sr, format="wav")

            candidate = self._generate_chunk(text, ref_path, language_id)
            if not isinstance(candidate, torch.Tensor):
                candidate = torch.tensor(candidate)
            while candidate.dim() > 2:
                candidate = candidate.squeeze(0)
            if candidate.dim() == 1:
                candidate = candidate.unsqueeze(0)

            candidate = self._cap_runaway_generation(candidate, text, self.model.sr)
            candidate = self._trim_trailing_silence(candidate, self.model.sr)
            candidate = torch.clamp(candidate, -1.0, 1.0)

            with tempfile.NamedTemporaryFile(suffix="_raw.wav", delete=False) as f:
                raw_out_path = f.name
            ta.save(raw_out_path, candidate, self.model.sr, format="wav")

            tmp_path_out = raw_out_path + "_post.wav"
            if postprocess_output_audio(raw_out_path, tmp_path_out, sample_rate=self.model.sr):
                with open(tmp_path_out, "rb") as f:
                    final_bytes = f.read()
            else:
                with open(raw_out_path, "rb") as f:
                    final_bytes = f.read()

            audio_b64 = base64.b64encode(final_bytes).decode("ascii")
            return CloneResponse(success=True, audio_b64=audio_b64).model_dump()

        except Exception as exc:
            return CloneResponse(success=False, error=str(exc)).model_dump()
        finally:
            for p in (tmp_path, ref_path, raw_out_path, tmp_path_out):
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
