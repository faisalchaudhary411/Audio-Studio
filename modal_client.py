"""
modal_client.py — Central Unified Dispatcher for VoxCraft Audio Studio
Routes automatically to modal_clone (Chatterbox) or modal_f5tts (F5-TTS)
"""

import modal_clone
import modal_f5tts


def is_configured() -> bool:
    """Check if any backend route is configured properly."""
    return modal_clone.is_configured() or modal_f5tts.is_configured()


def generate(text: str, reference_audio_b64: str, language_id: str = "en") -> dict:
    """
    Main entry point expected by clone_engine.py.
    - Scripts < 2000 chars -> Chatterbox Parallel Route (modal_clone.py)
    - Scripts >= 2000 chars -> F5-TTS Parallel Route (modal_f5tts.py)
    """
    char_count = len(text.strip())

    # Route 1: Long Scripts to F5-TTS
    if char_count >= 2000:
        if modal_f5tts.is_configured():
            return modal_f5tts.generate_long_audio(text, reference_audio_b64)
        # Fallback to Chatterbox if F5-TTS endpoint is missing
        elif modal_clone.is_configured():
            return modal_clone.generate_audio(text, reference_audio_b64, language_id=language_id)
        else:
            return {"success": False, "error": "No Modal TTS workers are configured."}

    # Route 2: Standard/Short Scripts to Chatterbox
    else:
        if modal_clone.is_configured():
            return modal_clone.generate_audio(text, reference_audio_b64, language_id=language_id)
        # Fallback to F5-TTS if Chatterbox endpoint is missing
        elif modal_f5tts.is_configured():
            return modal_f5tts.generate_long_audio(text, reference_audio_b64)
        else:
            return {"success": False, "error": "No Modal TTS workers are configured."}
