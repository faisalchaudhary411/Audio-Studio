"""
audio_tools.py — Transcribe / Convert / Merge / Cutter, ported from the
Streamlit app's respective tool_page blocks.

Ported faithfully:
- Transcribe: chunked (50s) Google Speech Recognition, since the free endpoint
  chokes on long single requests. Whisper is intentionally NOT re-enabled —
  the original code disabled it for the same reason noted in your comments:
  it loads a ~140MB local model with no timeout, which OOMs/hangs on
  lightweight hosting. Leave it disabled unless you move to real GPU infra.
- Convert: pydub + ffmpeg, arbitrary format + bitrate.
- Merge: pydub concatenation with a configurable silence gap.
- Cutter: trim (start/end) and split-at-time, both via pydub slicing.
"""

import io
import os
import math
import tempfile

from pydub import AudioSegment

MAX_UPLOAD_MB = 10

LANG_OPTIONS = {
    "English (US)": "en-US", "English (UK)": "en-GB", "Spanish": "es-ES", "French": "fr-FR",
    "German": "de-DE", "Italian": "it-IT", "Portuguese": "pt-BR", "Russian": "ru-RU",
    "Japanese": "ja-JP", "Korean": "ko-KR", "Chinese (Mandarin)": "zh-CN",
    "Arabic": "ar-SA", "Hindi": "hi-IN", "Turkish": "tr-TR", "Polish": "pl-PL", "Dutch": "nl-NL",
}


def check_file_size(file_bytes: bytes, max_mb: int = MAX_UPLOAD_MB):
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_mb:
        raise ValueError(f"File is {size_mb:.1f}MB — max allowed is {max_mb}MB.")


def _load_segment(file_bytes: bytes, filename: str) -> AudioSegment:
    suffix = "." + filename.rsplit(".", 1)[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        return AudioSegment.from_file(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _export_bytes(segment: AudioSegment, fmt: str, bitrate_kbps: int = None) -> bytes:
    buf = io.BytesIO()
    kwargs = {"format": fmt}
    if bitrate_kbps:
        kwargs["bitrate"] = f"{bitrate_kbps}k"
    segment.export(buf, **kwargs)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Transcribe
# ---------------------------------------------------------------------------
def transcribe(file_bytes: bytes, filename: str, lang_code: str) -> dict:
    check_file_size(file_bytes)
    audio = _load_segment(file_bytes, filename).set_frame_rate(16000).set_channels(1)

    import speech_recognition as sr
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.operation_timeout = 25

    CHUNK_MS = 50 * 1000
    total_chunks = max(1, math.ceil(len(audio) / CHUNK_MS))
    chunk_texts = []
    chunk_failures = 0

    for ci in range(total_chunks):
        chunk = audio[ci * CHUNK_MS: (ci + 1) * CHUNK_MS]
        if len(chunk) == 0:
            continue
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            chunk.export(tmp.name, format="wav")
            chunk_path = tmp.name
        try:
            with sr.AudioFile(chunk_path) as source:
                r.adjust_for_ambient_noise(source, duration=min(0.5, len(chunk) / 1000))
                audio_data = r.record(source)
            chunk_texts.append(r.recognize_google(audio_data, language=lang_code))
        except sr.UnknownValueError:
            pass
        except Exception:
            chunk_failures += 1
        finally:
            if os.path.exists(chunk_path):
                os.unlink(chunk_path)

    if not chunk_texts:
        if chunk_failures == total_chunks:
            raise Exception("Speech recognition service unavailable. Please try again in a moment.")
        raise Exception("Could not understand the audio. Try a clearer recording with less background noise.")

    text = " ".join(chunk_texts).strip()
    method = "Google Speech (standard)" if total_chunks == 1 else f"Google Speech ({len(chunk_texts)}/{total_chunks} segments)"
    return {"text": text, "method": method}


# ---------------------------------------------------------------------------
# Convert
# ---------------------------------------------------------------------------
def convert(file_bytes: bytes, filename: str, output_format: str, quality_kbps: int) -> bytes:
    check_file_size(file_bytes)
    audio = _load_segment(file_bytes, filename)
    return _export_bytes(audio, output_format, quality_kbps)


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------
def merge(files: list, gap_ms: int, output_format: str) -> bytes:
    """files: list of (file_bytes, filename) tuples, in the desired order."""
    if len(files) < 2:
        raise ValueError("Upload at least 2 files to merge.")
    combined = AudioSegment.empty()
    for i, (file_bytes, filename) in enumerate(files):
        check_file_size(file_bytes)
        combined += _load_segment(file_bytes, filename)
        if i < len(files) - 1:
            combined += AudioSegment.silent(duration=gap_ms)
    return _export_bytes(combined, output_format)


# ---------------------------------------------------------------------------
# Cutter
# ---------------------------------------------------------------------------
def get_duration_sec(file_bytes: bytes, filename: str) -> float:
    check_file_size(file_bytes)
    return len(_load_segment(file_bytes, filename)) / 1000


def trim(file_bytes: bytes, filename: str, start_sec: float, end_sec: float) -> bytes:
    check_file_size(file_bytes)
    audio = _load_segment(file_bytes, filename)
    trimmed = audio[int(start_sec * 1000):int(end_sec * 1000)]
    return _export_bytes(trimmed, "mp3")


def split(file_bytes: bytes, filename: str, split_sec: float) -> tuple:
    check_file_size(file_bytes)
    audio = _load_segment(file_bytes, filename)
    part1 = audio[:int(split_sec * 1000)]
    part2 = audio[int(split_sec * 1000):]
    return _export_bytes(part1, "mp3"), _export_bytes(part2, "mp3")
