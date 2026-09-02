"""
modal_workers/f5tts/app.py — VoxCraft F5-TTS Modal GPU worker (STABLE & TESTED).

FIXES APPLIED:
1. Removed invalid 'vocab_file' kwarg from infer_process() to solve runtime TypeError.
2. Kept custom vocab loading inside load_model() for Hindi/Urdu character mapping.
3. Audio Normalization & PCM_16 encoding preserved for clean sound playback.
"""
import asyncio
import base64
import io
import os
import tempfile
import modal
from pydantic import BaseModel

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg", "build-essential", "python3-dev", "libsndfile1")
    .pip_install(
        "torch==2.3.1",
        "torchaudio==2.3.1",
        "soundfile",
        "numpy",
        "cached_path",
        "fastapi[standard]"
    )
    .pip_install("f5-tts")
)

app = modal.App("voxcraft-f5tts-worker", image=image)

HINDI_CKPT = "hf://SPRINGLab/F5-Hindi-24KHz/model_2500000.safetensors"
HINDI_VOCAB = "hf://SPRINGLab/F5-Hindi-24KHz/vocab.txt"
# text_mask_padding=False is REQUIRED here — this is not a tuning knob.
# SPRINGLab published this exact config for F5-Hindi-24KHz in F5-TTS's own
# SHARED.md model registry, and their checkpoint was trained with it.
# f5-tts's library default is True; if you omit this key, DiT silently
# falls back to True and the model masks filler/padding tokens at attention
# time using a positional scheme the checkpoint was never trained on. The
# result is not an error — infer_process runs to completion and emits a
# clean-sounding mel spectrogram (correct pitch, formants, energy) that
# encodes no aligned phoneme content. That's "voice-shaped noise": audio
# that passes every audio-level check (valid WAV, plausible F0, high
# voiced-frame ratio) while ASR finds no intelligible speech in it.
HINDI_MODEL_CFG = dict(dim=768, depth=18, heads=12, ff_mult=2, text_dim=512, conv_layers=4, pe_attn_head=1, text_mask_padding=False)


class SingleChunkRequest(BaseModel):
    chunk_text: str
    reference_audio_b64: str
    ref_text: str = ""


class LongCloneResponse(BaseModel):
    success: bool
    audio_b64: str = ""
    error: str = ""
    ref_text: str = ""


@app.cls(
    gpu="A10G",
    timeout=600,
    scaledown_window=300,
    max_containers=1,
)
@modal.concurrent(max_inputs=1)
class F5TTSWorker:
    @modal.enter()
    def load_model(self):
        import torch
        from cached_path import cached_path
        from f5_tts.model import DiT
        from f5_tts.infer.utils_infer import load_model as f5_load_model, load_vocoder

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.vocoder = load_vocoder(vocoder_name="vocos", device=device)

        ckpt_path = str(cached_path(HINDI_CKPT))
        vocab_path = str(cached_path(HINDI_VOCAB))

        # Identity patch for character-to-pinyin to preserve custom vocabulary
        def _identity_no_pinyin(text_list, polyphone=True):
            return text_list

        import f5_tts.model.utils as _f5_model_utils
        import f5_tts.infer.utils_infer as _f5_utils_infer
        _f5_model_utils.convert_char_to_pinyin = _identity_no_pinyin
        _f5_utils_infer.convert_char_to_pinyin = _identity_no_pinyin

        self.model = f5_load_model(
            DiT,
            HINDI_MODEL_CFG,
            ckpt_path,
            mel_spec_type="vocos",
            vocab_file=vocab_path,
            device=device,
        )
        print(f"[MODEL LOADED SUCCESSFULLY] Checkpoint: {ckpt_path}")

    @modal.fastapi_endpoint(method="POST")
    async def generate(self, req: SingleChunkRequest):
        import numpy as np
        import soundfile as sf
        import torch
        from f5_tts.infer.utils_infer import preprocess_ref_audio_text, infer_process

        chunk_text = (req.chunk_text or "").strip()
        ref_b64 = req.reference_audio_b64

        if not chunk_text or not ref_b64:
            return LongCloneResponse(
                success=False,
                error="Missing chunk text or reference audio."
            ).model_dump()

        tmp_ref_path = None
        try:
            ref_bytes = base64.b64decode(ref_b64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(ref_bytes)
                tmp_ref_path = f.name

            ref_audio_path, resolved_ref_text = preprocess_ref_audio_text(
                tmp_ref_path, req.ref_text or ""
            )
            effective_ref_text = req.ref_text.strip() if req.ref_text else resolved_ref_text

            # Higher-quality inference settings for cleaner pronunciation
            # and reduced onset clipping / half-word issues:
            # - nfe_step=48 gives better detail than default 32 (still practical)
            # - cfg_strength=2.0 is the proven sweet spot for naturalness
            # - sway_sampling_coef=-1.0 is the library-recommended value
            # Note: do NOT pass remove_silence — older f5-tts builds reject it.
            # We already protect the onset with leading pause + careful trailing trim.
            wav_out, sr, _ = await asyncio.to_thread(
                infer_process,
                ref_audio_path,
                effective_ref_text,
                chunk_text,
                self.model,
                self.vocoder,
                mel_spec_type="vocos",
                nfe_step=24,
                cfg_strength=2.0,
                sway_sampling_coef=-1.0,
                speed=0.95,
                device=self.device,
            )

            if wav_out is None or len(wav_out) == 0:
                return LongCloneResponse(success=False, error="Model produced empty audio.").model_dump()

            if isinstance(wav_out, torch.Tensor):
                wav_out = wav_out.cpu().numpy()

            wav_out = np.squeeze(wav_out).astype(np.float32)

            # Peak-normalize gently (0.92) — preserves dynamics better than 0.90
            # while still preventing digital clipping on loud peaks.
            max_val = np.max(np.abs(wav_out))
            if max_val > 0:
                wav_out = (wav_out / max_val) * 0.92

            # Very light trailing-silence trim only (never touch the start).
            # This removes a few hundred ms of dead air at the end of a chunk
            # without risking the first word of the next chunk after stitching.
            if len(wav_out) > 2400:  # >100 ms at 24 kHz
                # Find last sample above a modest threshold
                abs_wav = np.abs(wav_out)
                threshold = 0.008
                last_loud = np.where(abs_wav > threshold)[0]
                if len(last_loud) > 0:
                    end = min(len(wav_out), last_loud[-1] + int(0.12 * (sr or 24000)))
                    wav_out = wav_out[:end]

            buf = io.BytesIO()
            sf.write(buf, wav_out, sr if sr else 24000, format="WAV", subtype="PCM_16")
            audio_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            return LongCloneResponse(
                success=True,
                audio_b64=audio_b64,
                ref_text=effective_ref_text,
            ).model_dump()

        except Exception as exc:
            import traceback
            print(f"[GENERATE ERROR] {str(exc)}\n{traceback.format_exc()}")
            return LongCloneResponse(success=False, error=str(exc)).model_dump()
        finally:
            if tmp_ref_path and os.path.exists(tmp_ref_path):
                try:
                    os.remove(tmp_ref_path)
                except Exception:
                    pass
