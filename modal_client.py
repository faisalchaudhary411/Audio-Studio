"""
modal_client.py — Central Dispatcher for VoxCraft Audio Studio

Deliberately has NO automatic/length-based/silent-fallback routing
anymore. An earlier version guessed which backend to use from text length
and silently fell back to whichever worker happened to be configured —
that caused a real incident where Chatterbox was misconfigured and every
request silently generated on F5-TTS instead, undetected until someone
noticed the wrong voice/quality. The engine is now always an explicit
choice from the caller (surfaced as a dropdown in Studio), and if that
engine isn't configured or fails, the error says so plainly instead of
quietly switching engines.
"""

import modal_clone
import modal_f5tts

VALID_ENGINES = ("chatterbox", "f5tts")

# F5-TTS's deployed checkpoint (SPRINGLab/F5-Hindi-24KHz) is Hindi-only —
# see modal_f5tts.py's docstring. Plain English text would silently
# mispronounce rather than error, so it's blocked here at dispatch time.
F5TTS_SUPPORTED_LANGUAGES = ("hi",)


def is_configured() -> bool:
    """True if at least one backend is reachable — used only for the
    upfront "is cloning available at all on this deployment" check, not
    for choosing between engines."""
    return modal_clone.is_configured() or modal_f5tts.is_configured()


def engine_is_configured(engine: str) -> bool:
    if engine == "chatterbox":
        return modal_clone.is_configured()
    if engine == "f5tts":
        return modal_f5tts.is_configured()
    return False


def generate(text: str, reference_audio_b64: str, language_id: str = "en",
             engine: str = "chatterbox", ref_text: str = "") -> dict:
    """
    Main entry point expected by clone_engine.py. `engine` must be an
    explicit choice ("chatterbox" or "f5tts") — there is no automatic
    routing or fallback between them.

    ref_text: optional exact transcript of the reference audio. Only used
    by the F5-TTS path. Strongly improves quality and prevents noise-only
    output when the automatic ASR would otherwise produce a bad transcript.
    """
    if engine not in VALID_ENGINES:
        return {"success": False, "error": f"Unknown engine '{engine}'. Choose one of: {', '.join(VALID_ENGINES)}."}

    if engine == "f5tts" and language_id not in F5TTS_SUPPORTED_LANGUAGES:
        return {
            "success": False,
            "error": "The F5-TTS engine on this deployment only supports Hindi/Urdu text. Switch to Chatterbox for English.",
        }

    if engine == "chatterbox":
        if not modal_clone.is_configured():
            return {"success": False, "error": "Chatterbox engine is not configured on this deployment (MODAL_CLONE_ENDPOINT_URL missing)."}
        return modal_clone.generate_audio(text, reference_audio_b64, language_id=language_id)

    # engine == "f5tts"
    if not modal_f5tts.is_configured():
        return {"success": False, "error": "F5-TTS engine is not configured on this deployment (MODAL_F5TTS_ENDPOINT_URL missing)."}
    return modal_f5tts.generate_long_audio(text, reference_audio_b64, ref_text=ref_text)
