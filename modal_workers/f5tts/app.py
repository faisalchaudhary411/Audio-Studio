"""
modal_workers/f5tts/app.py — VoxCraft F5-TTS Modal GPU worker (UPDATED FOR LATEST MODAL SDK).

FIXES APPLIED:
1. Replaced deprecated 'concurrency_limit' with 'max_containers=1'.
2. Applied '@modal.concurrent(max_inputs=1)' at CLASS LEVEL (per new Modal syntax).
3. Preserved Devanagari/Hindi patching logic and cleanup routines.
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
        "cached_path",
        "fastapi[standard]"
    )
    .pip_install("f5-tts")
)

app = modal.App("voxcraft-f5tts-worker", image=image)

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
    ref_text: str = ""


@app.cls(
    gpu="A10G",
    timeout=600,
    scaledown_window=300,
    max_containers=1,
)
@modal.concurrent(max_inputs=1)  # FIX: Applied at Class Level as required by Modal
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

        # Patch convert_char_to_pinyin to identity for Devanagari
        def _identity_no_pinyin(text_list, polyphone=True):
            return text_list

        import f5_tts.model.utils as _f5_model_utils
        import f5_tts.infer.utils_infer as _f5_utils_infer
        _f5_model_utils.convert_char_to_pinyin = _identity_no_pinyin
        _f5_utils_infer.convert_char_to_pinyin = _identity_no_pinyin

        _test_in = ["देवनागरी टेस्ट"]
        _test_out = _f5_utils_infer.convert_char_to_pinyin(_test_in)
        print(f"[PATCH CHECK] convert_char_to_pinyin patched={_test_out == _test_in}")

        # Force Hindi transcription for reference audio
        _original_transcribe = _f5_utils_infer.transcribe

        def _transcribe_force_hindi(ref_audio, language=None):
            return _original_transcribe(ref_audio, language="hindi")

        _f5_utils_infer.transcribe = _transcribe_force_hindi

        ckpt_path = str(cached_path(HINDI_CKPT))
        vocab_path = str(cached_path(HINDI_VOCAB))
        self.model = f5_load_model(
            DiT,
            HINDI_MODEL_CFG,
            ckpt_path,
            mel_spec_type="vocos",
            vocab_file=vocab_path,
            device=device,
        )
        print(f"[MODEL LOADED] checkpoint={ckpt_path} device={device}")

        # STARTUP VALIDATION
        from f5_tts.infer.utils_infer import infer_process
        import numpy as np
        import soundfile as sf

        test_sr = 24000
        test_duration = 1.0
        test_wav = np.zeros(int(test_sr * test_duration), dtype=np.float32)
        test_path = "/tmp/_startup_test_ref.wav"
        sf.write(test_path, test_wav, test_sr)

        try:
            test_out, test_sr_out, _ = infer_process(
                test_path,
                "टेस्ट",
                "टेस्ट",
                self.model,
                self.vocoder,
                mel_spec_type="vocos",
                device=self.device,
            )
            assert test_out is not None and len(test_out) > 0, "Empty startup test output"
            assert np.isfinite(test_out).all(), "NaN/Inf in startup test output"
            print(f"[STARTUP TEST] PASSED — output length={len(test_out)} samples")
        except Exception as e:
            print(f"[STARTUP TEST] FAILED: {e}")
            raise RuntimeError(f"Model startup validation failed: {e}") from e
        finally:
            if os.path.exists(test_path):
                os.remove(test_path)

    @modal.fastapi_endpoint(method="POST")
    def generate(self, req: SingleChunkRequest):
        import soundfile as sf
        import numpy as np
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

            wav_out, sr, _ = infer_process(
                ref_audio_path,
                effective_ref_text,
                chunk_text,
                self.model,
                self.vocoder,
                mel_spec_type="vocos",
                device=self.device,
            )

            if wav_out is None or len(wav_out) == 0:
                return LongCloneResponse(
                    success=False,
                    error="Model produced empty audio."
                ).model_dump()

            if not np.isfinite(wav_out).all():
                return LongCloneResponse(
                    success=False,
                    error="Model produced invalid audio (NaN/Inf values)."
                ).model_dump()

            if len(wav_out) < 12000:  # < 0.5s at 24kHz
                return LongCloneResponse(
                    success=False,
                    error=f"Audio too short ({len(wav_out)} samples) — generation failed."
                ).model_dump()

            buf = io.BytesIO()
            sf.write(buf, wav_out, sr, format="WAV")
            audio_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            return LongCloneResponse(
                success=True,
                audio_b64=audio_b64,
                ref_text=effective_ref_text,
            ).model_dump()

        except Exception as exc:
            import traceback
            err_detail = f"{str(exc)}\n{traceback.format_exc()}"
            print(f"[GENERATE ERROR] {err_detail}")
            return LongCloneResponse(
                success=False,
                error=str(exc),
            ).model_dump()
        finally:
            if tmp_ref_path and os.path.exists(tmp_ref_path):
                try:
                    os.remove(tmp_ref_path)
                except Exception:
                    pass
