"""
clone_engine.py — voice cloning via Chatterbox-Turbo (Resemble AI, MIT license).

Why Chatterbox and not XTTS-v2: XTTS-v2 sounds like the obvious free choice but
its weights ship under the Coqui Public Model License, which is NON-COMMERCIAL
ONLY — and Coqui shut down in 2024, so there's no one left to sell a commercial
license from. Since VoxCraft is a paid product, that's a real legal exposure.
Chatterbox is MIT-licensed end to end (code + weights) — genuinely free for
commercial use.

Why Turbo (not the 0.5B Original/Multilingual variants): smallest footprint of
the family, meant to run without a GPU. Still noticeably heavier than edge-tts —
expect 10-60+ seconds per generation on Railway CPU, not instant.

Runs LAZILY: the model is not loaded until the first clone request, so idle
memory/CPU cost is near zero. Once loaded it stays warm in the process (which is
why this needs a long-running service like Railway, not serverless).
"""

import io
import threading
import uuid

_model = None
_model_lock = threading.Lock()

# In-memory job store. Fine for a single Railway instance; if you ever scale to
# multiple instances you'll need a shared store (Redis) instead of this dict.
_jobs = {}


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from chatterbox.tts_turbo import ChatterboxTurboTTS
                except ImportError:
                    raise Exception(
                        "Voice cloning isn't installed on this deployment yet. "
                        "Run `pip install -r requirements-clone.txt` on an instance "
                        "with enough RAM, then redeploy."
                    )
                _model = ChatterboxTurboTTS.from_pretrained(device="cpu")
    return _model


def _run_clone_job(job_id: str, text: str, reference_audio_path: str):
    _jobs[job_id]["status"] = "loading_model"
    try:
        model = _get_model()
        _jobs[job_id]["status"] = "generating"
        wav = model.generate(text, audio_prompt_path=reference_audio_path)

        buf = io.BytesIO()
        import torchaudio as ta
        ta.save(buf, wav, model.sr, format="wav")
        buf.seek(0)

        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["audio"] = buf.getvalue()
    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)


def start_clone_job(text: str, reference_audio_path: str) -> str:
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"status": "queued", "audio": None, "error": None}
    thread = threading.Thread(target=_run_clone_job, args=(job_id, text, reference_audio_path), daemon=True)
    thread.start()
    return job_id


def get_job(job_id: str):
    return _jobs.get(job_id)


def unload_model():
    """Free the Chatterbox model from RAM after cloning is done.
    Call this from app.py after a job reaches 'done' or 'error' status."""
    global _model
    with _model_lock:
        _model = None
    import gc
    gc.collect()
