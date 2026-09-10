"""
errors.py — shared UserFacingError exception.

Raise UserFacingError (instead of a bare Exception/ValueError) when a
message is deliberately written to be safe and useful for the end user —
validation messages ("file is too big"), rate-limit/retry prompts, etc.

api_error() in app.py passes UserFacingError messages through to the
client verbatim. Every other exception still gets genericized to
"Something went wrong trying to {action}" so internal details (file
paths, library tracebacks, ffmpeg/GPU-worker internals, etc.) never
leak to a client. See app.py's api_error() docstring for the full
rationale.

No third-party imports here on purpose — this module has to be safe to
import from both app.py and the lower-level modules (audio_tools.py,
clone_engine.py, music_engine.py, ...) without creating import cycles.
"""


class UserFacingError(Exception):
    """An exception whose str() is safe and intended to reach the end user."""
    pass
