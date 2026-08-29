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
        "cached_path",
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
    ref_text: str = ""

@app.cls(gpu="A10G", timeout=600, scaledown_window=300)
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

        # NOTE: the high-level f5_tts.api.F5TTS() convenience class does NOT
        # accept a custom model_cfg — it only knows a fixed set of named
        # presets internally, with no way to plug in a different
        # architecture (confirmed by a TypeError in production when this
        # was first tried). Custom checkpoints need the lower-level
        # load_model() function instead, which IS the same path F5-TTS's
        # own official Gradio app uses for its "load_custom()" — see
        # SWivid/F5-TTS app.py.
        # CRITICAL: F5-TTS's convert_char_to_pinyin() runs by default inside
        # infer_process() and inserts a space between every character of
        # any text whose UTF-8 byte pattern looks "East Asian" (3 bytes/char)
        # — which Devanagari matches too, not just CJK. That shreds
        # Devanagari words into isolated glyphs the model was never trained
        # on, producing exactly the "noise, no actual voice" failure. The
        # SPRINGLab/F5-Hindi-24KHz author confirmed this checkpoint was
        # trained WITHOUT this conversion — so inference must skip it too.
        # Same fix other non-Chinese F5-TTS fine-tunes (e.g. Japanese) have
        # needed.
        #
        # Patched in BOTH places it could be referenced from: the source
        # module (f5_tts.model.utils, in case infer_process re-imports it
        # fresh on every call) AND the consumer module (f5_tts.infer.utils_infer,
        # in case it kept a module-level reference bound at f5-tts's own
        # import time, which a source-only patch wouldn't reach). A
        # startup self-check logs whether this actually took — check
        # Modal's Logs tab for "convert_char_to_pinyin patch check" if
        # output is still garbled after this deploy.
        def _identity_no_pinyin(text_list, polyphone=True):
            return text_list

        import f5_tts.model.utils as _f5_model_utils
        import f5_tts.infer.utils_infer as _f5_utils_infer
        _f5_model_utils.convert_char_to_pinyin = _identity_no_pinyin
        _f5_utils_infer.convert_char_to_pinyin = _identity_no_pinyin

        _test_in = ["देवनागरी टेस्ट"]
        _test_out = _f5_utils_infer.convert_char_to_pinyin(_test_in)
        print(f"[convert_char_to_pinyin patch check] patched={_test_out == _test_in} in={_test_in} out={_test_out}")

        # SECOND FIX: preprocess_ref_audio_text() auto-transcribes the
        # reference clip when no ref_text is given, but never exposes a
        # language override — Whisper's own language auto-detection then
        # sometimes calls Hindi speech "Urdu" (same spoken language,
        # different script) and transcribes it in Nastaliq. That ref_text
        # is then completely out-of-vocabulary for this Devanagari-only
        # checkpoint, corrupting the reference conditioning (confirmed via
        # Modal logs showing a Nastaliq ref_text next to a Devanagari
        # gen_text). transcribe() itself DOES accept a language param, so
        # force it to Hindi here — preprocess_ref_audio_text calls
        # transcribe() by module-level name from within the same module,
        # so patching it here reliably intercepts that call.
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

    @modal.fastapi_endpoint(method="POST")
    def generate(self, req: SingleChunkRequest):
        import soundfile as sf
        from f5_tts.infer.utils_infer import preprocess_ref_audio_text, infer_process

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

            # preprocess_ref_audio_text trims silence/normalizes the clip and,
            # if ref_text is empty, runs local ASR (faster-whisper) to
            # transcribe it — same behavior the removed F5TTS.infer()
            # convenience method delegated to internally.
            ref_audio_path, ref_text = preprocess_ref_audio_text(tmp_ref_path, req.ref_text or "")

            wav_out, sr, _ = infer_process(
                ref_audio_path,
                ref_text,
                chunk_text,
                self.model,
                self.vocoder,
                mel_spec_type="vocos",
                device=self.device,
            )

            buf = io.BytesIO()
            sf.write(buf, wav_out, sr, format="WAV")
            audio_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            return LongCloneResponse(success=True, audio_b64=audio_b64, ref_text=ref_text).model_dump()

        except Exception as exc:
            return LongCloneResponse(success=False, error=str(exc)).model_dump()
        finally:
            if tmp_ref_path and os.path.exists(tmp_ref_path):
                try:
                    os.remove(tmp_ref_path)
                except Exception:
                    pass
