"""
features.py — central on/off switches for GPU-backed and Pro+ features.

STRATEGY (2026-10): VoxCraft is focusing on free/CPU audio tools first
(trim, denoise, convert, etc.) to rank on low-competition SEO keywords.
Everything that needs a paid GPU (voice cloning, ACE-Step AI music, Whisper)
is switched OFF by default, but NOTHING IS DELETED — flip an env var on the
VPS and restart the service to bring a feature back:

    PRO_PLUS_ENABLED=1       show/sell the Pro+ plan again (monthly + annual)
    VOICE_CLONE_ENABLED=1    re-open voice cloning (needs Modal workers deployed)
    MUSIC_GPU_ENABLED=1      use the ACE-Step GPU worker for /tools/ai-music-generator
                             (default is the built-in CPU code-based generator)
    REDUB_WHISPER_ENABLED=1  let Video Redub / Transcribe use Whisper on GPU
                             (default is Google Speech, free)
"""
import os


def _on(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


PRO_PLUS_ENABLED = _on("PRO_PLUS_ENABLED")
VOICE_CLONE_ENABLED = _on("VOICE_CLONE_ENABLED")
MUSIC_GPU_ENABLED = _on("MUSIC_GPU_ENABLED")
REDUB_WHISPER_ENABLED = _on("REDUB_WHISPER_ENABLED")

# Message used by every disabled clone endpoint
VOICE_CLONE_COMING_SOON = (
    "Voice cloning is coming soon. We're focusing on our audio tools first — "
    "check back shortly."
)
