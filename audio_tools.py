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
    kwargs = {}
    if bitrate_kbps:
        kwargs["bitrate"] = f"{bitrate_kbps}k"

    # BUG FIX: "m4a" isn't a real ffmpeg muxer name (it's just the file
    # extension convention) — ffmpeg needs the "ipod" muxer + aac codec to
    # actually produce a valid .m4a file. Passing format="m4a" straight
    # through failed with "Requested output format 'm4a' is not known."
    if fmt == "m4a":
        kwargs["format"] = "ipod"
        kwargs["codec"] = "aac"
    else:
        kwargs["format"] = fmt

    try:
        segment.export(buf, **kwargs)
    except Exception as e:
        raise Exception(f"Could not encode to {fmt.upper()}: {str(e)[:200]}")
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


# ---------------------------------------------------------------------------
# Denoise
# ---------------------------------------------------------------------------
def denoise(file_bytes: bytes, filename: str, strength: float = 0.5) -> bytes:
    """Ported from the Streamlit denoise tool. Note: downmixes to mono during
    processing (same limitation as the original — noisereduce operates on a
    1D sample array)."""
    check_file_size(file_bytes)
    import numpy as np
    import noisereduce as nr

    audio = _load_segment(file_bytes, filename)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    reduced = nr.reduce_noise(y=samples, sr=audio.frame_rate, prop_decrease=strength)
    reduced_int16 = np.clip(reduced, -32768, 32767).astype(np.int16)

    reduced_audio = AudioSegment(
        reduced_int16.tobytes(), frame_rate=audio.frame_rate, sample_width=2, channels=1
    )
    return _export_bytes(reduced_audio, "mp3")


# ---------------------------------------------------------------------------
# Voice Changer — Pitch Shift / Robot / Echo / Chipmunk / Deep Voice
# ---------------------------------------------------------------------------
def voice_change(file_bytes: bytes, filename: str, effect: str, **params) -> bytes:
    check_file_size(file_bytes)
    import numpy as np
    audio = _load_segment(file_bytes, filename)

    if effect == "pitch_shift":
        # BUG FIX: the old implementation changed the sample rate to fake a
        # pitch shift (the classic "cheap" trick), but that also sped up or
        # slowed down playback — shifting up 5 semitones made the clip ~25%
        # shorter, which isn't what a "Pitch Shift" effect should do. Real
        # pitch-shifting needs to change pitch WITHOUT changing duration —
        # librosa.effects.pitch_shift does this properly (phase vocoder +
        # resampling under the hood), verified it preserves exact sample
        # count before wiring this in.
        semitones = params.get("semitones", 0)
        if semitones != 0:
            import librosa
            samples_f = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
            if audio.channels == 2:
                samples_f = samples_f.reshape((-1, 2)).T  # librosa wants (channels, samples) for stereo
                shifted = librosa.effects.pitch_shift(samples_f, sr=audio.frame_rate, n_steps=semitones)
                shifted = shifted.T.flatten()
            else:
                shifted = librosa.effects.pitch_shift(samples_f, sr=audio.frame_rate, n_steps=semitones)
            shifted_int16 = np.clip(shifted * 32768.0, -32768, 32767).astype(np.int16)
            result = AudioSegment(shifted_int16.tobytes(), frame_rate=audio.frame_rate,
                                   sample_width=2, channels=audio.channels)
        else:
            result = audio

    elif effect == "robot":
        # Slight improvement: bounded modulation depth (never fully inverts
        # phase at max intensity, which caused harsh digital clicking) and a
        # lower carrier frequency more typical of a "robotic" ring-mod effect.
        intensity = params.get("intensity", 0.5)
        samples = np.array(audio.get_array_of_samples())
        t = np.linspace(0, len(samples) / audio.frame_rate, len(samples))
        carrier = np.sin(2 * np.pi * 60 * t)
        depth = 0.75 * intensity  # capped so the modulation never fully cancels the signal
        robot_samples = samples * (1 - depth + depth * carrier)
        robot_samples = np.clip(robot_samples, -32768, 32767).astype(np.int16)
        result = AudioSegment(robot_samples.tobytes(), frame_rate=audio.frame_rate,
                               sample_width=audio.sample_width, channels=audio.channels)

    elif effect == "echo":
        delay_ms = params.get("delay_ms", 200)
        decay = params.get("decay", 0.5)
        samples = np.array(audio.get_array_of_samples())
        delay_samples = int(delay_ms * audio.frame_rate / 1000)
        echoed = samples.copy()
        if delay_samples < len(samples):
            echoed[delay_samples:] += (samples[:-delay_samples] * decay).astype(samples.dtype)
        echoed = np.clip(echoed, -32768, 32767).astype(np.int16)
        result = AudioSegment(echoed.tobytes(), frame_rate=audio.frame_rate,
                               sample_width=audio.sample_width, channels=audio.channels)

    elif effect == "chipmunk":
        new_rate = int(audio.frame_rate * 1.5)
        result = audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate})
        result = result.set_frame_rate(audio.frame_rate)

    elif effect == "deep_voice":
        new_rate = int(audio.frame_rate * 0.7)
        result = audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate})
        result = result.set_frame_rate(audio.frame_rate)

    else:
        raise ValueError(f"Unknown effect: {effect}")

    return _export_bytes(result, "mp3")


# ---------------------------------------------------------------------------
# Video to Audio — direct ffmpeg subprocess, not pydub (matches original)
# ---------------------------------------------------------------------------
def video_to_audio(file_bytes: bytes, filename: str, output_format: str = "mp3", quality_kbps: int = 192) -> bytes:
    check_file_size(file_bytes, max_mb=50)
    video_path, output_path = None, None
    try:
        suffix = "." + filename.rsplit(".", 1)[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            video_path = tmp.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}") as out_tmp:
            output_path = out_tmp.name

        import subprocess
        try:
            subprocess.run(
                ["ffmpeg", "-i", video_path, "-vn", "-ar", "44100", "-ac", "2",
                 "-b:a", f"{quality_kbps}k", output_path, "-y"],
                check=True, capture_output=True, timeout=120,
            )
        except FileNotFoundError:
            raise Exception("ffmpeg is required for video-to-audio extraction and isn't installed on this server.")
        except subprocess.CalledProcessError:
            # Almost always a partial/corrupted upload (common on slow mobile
            # data), not actually a missing-ffmpeg problem.
            raise Exception("Could not read this video file. If you're on mobile data, this can happen when the upload doesn't fully finish — please try uploading again.")

        with open(output_path, "rb") as f:
            return f.read()
    finally:
        for p in (video_path, output_path):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass
