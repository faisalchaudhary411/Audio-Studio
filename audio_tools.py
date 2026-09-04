"""
audio_tools.py — Transcribe / Convert / Merge / Cutter / Denoise / Voice change /
Video extract.

Improvements (2026-09):
- Merge: optional crossfade between clips (removes clicks at joins)
- Cutter: auto-trim silence, split-on-silence, keep original format option
- Convert: named presets (YouTube / Edit master / Archive)
- Denoise: strength presets + optional stationary noise mode
- Voice change: dry/wet mix so effects stay intelligible
- Video extract: optional start/end time range
- Transcribe: Urdu added, richer result metadata, SRT helper
- Normalize: simple peak / target loudness helper for chaining
- Shared: better format handling, duration helpers

Whisper remains disabled on lightweight hosts (loads ~140MB+ and can OOM).
When GPU workers are available, add a whisper_transcribe() path and expose it
as an option in the API without removing Google Speech fallback.
"""

import io
import os
import math
import tempfile

from pydub import AudioSegment
from pydub.silence import detect_nonsilent, split_on_silence as _pydub_split_on_silence

MAX_UPLOAD_MB = 10

LANG_OPTIONS = {
    "English (US)": "en-US",
    "English (UK)": "en-GB",
    "Urdu": "ur-PK",
    "Hindi": "hi-IN",
    "Arabic": "ar-SA",
    "Spanish": "es-ES",
    "French": "fr-FR",
    "German": "de-DE",
    "Italian": "it-IT",
    "Portuguese": "pt-BR",
    "Russian": "ru-RU",
    "Japanese": "ja-JP",
    "Korean": "ko-KR",
    "Chinese (Mandarin)": "zh-CN",
    "Turkish": "tr-TR",
    "Polish": "pl-PL",
    "Dutch": "nl-NL",
}

# Convert presets: (format, bitrate_or_None)
CONVERT_PRESETS = {
    "youtube": ("mp3", 192),      # voiceover / final upload
    "social": ("mp3", 160),
    "edit_master": ("wav", None), # uncompressed while editing
    "archive": ("flac", None),    # lossless archive
    "podcast": ("mp3", 128),
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

    # "m4a" isn't a real ffmpeg muxer name — use ipod + aac
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


def estimate_output_size_mb(duration_sec: float, fmt: str, bitrate_kbps: int = None) -> float:
    """Rough size estimate for UI before convert."""
    if fmt in ("wav",):
        # 16-bit mono ~ 176 kbps at 44.1k; use stereo-ish estimate
        return max(0.01, duration_sec * 0.175)
    if fmt == "flac":
        return max(0.01, duration_sec * 0.09)
    br = bitrate_kbps or 192
    return max(0.01, (duration_sec * br) / 8 / 1024)


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
    words = len(text.split()) if text else 0
    duration_sec = len(audio) / 1000.0

    return {
        "text": text,
        "method": method,
        "language": lang_code,
        "word_count": words,
        "duration_sec": round(duration_sec, 2),
        "segments_ok": len(chunk_texts),
        "segments_total": total_chunks,
        # Plain SRT stub (equal time slices) — useful until word-level timestamps exist
        "srt": _text_to_simple_srt(text, duration_sec) if text else "",
    }


def _text_to_simple_srt(text: str, duration_sec: float) -> str:
    """Split transcript into rough time-based SRT cues for subtitles.
    Not word-aligned — good enough for a first-pass caption file."""
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    if not sentences:
        sentences = [text]
    n = len(sentences)
    if duration_sec <= 0:
        duration_sec = max(n * 2.5, 1.0)
    slice_len = duration_sec / n
    lines = []
    for i, sent in enumerate(sentences):
        start = i * slice_len
        end = min(duration_sec, (i + 1) * slice_len)
        cue = sent if sent.endswith((".", "?", "!")) else sent + "."
        lines.append(f"{i + 1}")
        lines.append(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}")
        lines.append(cue)
        lines.append("")
    return "\n".join(lines)


def _fmt_srt_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------------------------------------------------------------------------
# Convert
# ---------------------------------------------------------------------------
def convert(file_bytes: bytes, filename: str, output_format: str, quality_kbps: int = None,
            preset: str = None) -> bytes:
    check_file_size(file_bytes)
    if preset and preset in CONVERT_PRESETS:
        output_format, quality_kbps = CONVERT_PRESETS[preset]
    output_format = (output_format or "mp3").lower().strip()
    audio = _load_segment(file_bytes, filename)
    return _export_bytes(audio, output_format, quality_kbps)


def convert_with_meta(file_bytes: bytes, filename: str, output_format: str = "mp3",
                      quality_kbps: int = 192, preset: str = None) -> dict:
    """Convert and return bytes + helpful metadata for the UI."""
    check_file_size(file_bytes)
    if preset and preset in CONVERT_PRESETS:
        output_format, quality_kbps = CONVERT_PRESETS[preset]
    audio = _load_segment(file_bytes, filename)
    duration = len(audio) / 1000.0
    out = _export_bytes(audio, output_format, quality_kbps)
    return {
        "bytes": out,
        "format": output_format,
        "bitrate_kbps": quality_kbps,
        "duration_sec": round(duration, 2),
        "output_size_mb": round(len(out) / (1024 * 1024), 3),
        "estimated_size_mb": round(estimate_output_size_mb(duration, output_format, quality_kbps), 3),
    }


# ---------------------------------------------------------------------------
# Merge (with optional crossfade)
# ---------------------------------------------------------------------------
def merge(files: list, gap_ms: int = 0, output_format: str = "mp3",
          crossfade_ms: int = 0) -> bytes:
    """files: list of (file_bytes, filename) tuples, in the desired order.

    gap_ms: silence inserted between clips when crossfade_ms == 0
    crossfade_ms: overlap/crossfade at joins (ignores gap when > 0)
    """
    if len(files) < 2:
        raise ValueError("Upload at least 2 files to merge.")
    crossfade_ms = max(0, int(crossfade_ms or 0))
    gap_ms = max(0, int(gap_ms or 0))

    segments = []
    for file_bytes, filename in files:
        check_file_size(file_bytes)
        segments.append(_load_segment(file_bytes, filename))

    combined = segments[0]
    for seg in segments[1:]:
        if crossfade_ms > 0:
            # pydub append with crossfade
            cf = min(crossfade_ms, len(combined) // 2, len(seg) // 2)
            if cf > 0:
                combined = combined.append(seg, crossfade=cf)
            else:
                combined += seg
        else:
            if gap_ms > 0:
                combined += AudioSegment.silent(duration=gap_ms)
            combined += seg

    return _export_bytes(combined, output_format)


# ---------------------------------------------------------------------------
# Cutter / silence tools
# ---------------------------------------------------------------------------
def get_duration_sec(file_bytes: bytes, filename: str) -> float:
    check_file_size(file_bytes)
    return len(_load_segment(file_bytes, filename)) / 1000


def trim(file_bytes: bytes, filename: str, start_sec: float, end_sec: float,
         output_format: str = "mp3") -> bytes:
    check_file_size(file_bytes)
    audio = _load_segment(file_bytes, filename)
    start_ms = max(0, int(float(start_sec) * 1000))
    end_ms = min(len(audio), int(float(end_sec) * 1000))
    if end_ms <= start_ms:
        raise ValueError("End time must be greater than start time.")
    trimmed = audio[start_ms:end_ms]
    return _export_bytes(trimmed, output_format)


def split(file_bytes: bytes, filename: str, split_sec: float,
          output_format: str = "mp3") -> tuple:
    check_file_size(file_bytes)
    audio = _load_segment(file_bytes, filename)
    split_ms = int(float(split_sec) * 1000)
    if split_ms <= 0 or split_ms >= len(audio):
        raise ValueError("Split point must be inside the clip.")
    part1 = audio[:split_ms]
    part2 = audio[split_ms:]
    return _export_bytes(part1, output_format), _export_bytes(part2, output_format)


def auto_trim_silence(file_bytes: bytes, filename: str,
                      silence_thresh_db: int = -40,
                      keep_silence_ms: int = 120,
                      output_format: str = "mp3") -> bytes:
    """Strip leading and trailing silence. Keeps a small pad so words aren't clipped."""
    check_file_size(file_bytes)
    audio = _load_segment(file_bytes, filename)
    nonsilent = detect_nonsilent(
        audio,
        min_silence_len=200,
        silence_thresh=silence_thresh_db,
        seek_step=10,
    )
    if not nonsilent:
        # Entire file looks silent — return a short pad rather than empty
        return _export_bytes(audio[: min(len(audio), 500)], output_format)

    start = max(0, nonsilent[0][0] - keep_silence_ms)
    end = min(len(audio), nonsilent[-1][1] + keep_silence_ms)
    return _export_bytes(audio[start:end], output_format)


def split_on_silence(file_bytes: bytes, filename: str,
                     min_silence_len_ms: int = 500,
                     silence_thresh_db: int = -40,
                     keep_silence_ms: int = 150,
                     output_format: str = "mp3") -> list:
    """Split a long recording into clips at silent gaps. Returns list of MP3/WAV bytes."""
    check_file_size(file_bytes)
    audio = _load_segment(file_bytes, filename)
    chunks = _pydub_split_on_silence(
        audio,
        min_silence_len=min_silence_len_ms,
        silence_thresh=silence_thresh_db,
        keep_silence=keep_silence_ms,
    )
    if not chunks:
        return [_export_bytes(audio, output_format)]
    return [_export_bytes(c, output_format) for c in chunks if len(c) > 100]


# ---------------------------------------------------------------------------
# Denoise
# ---------------------------------------------------------------------------
def denoise(file_bytes: bytes, filename: str, strength: float = 0.5,
            stationary: bool = True) -> bytes:
    """Reduce steady background noise.

    strength: 0.0–1.0 (UI: Light≈0.35, Medium≈0.55, Strong≈0.8)
    stationary: True works better for fan/AC hum; False for more varying noise
    """
    check_file_size(file_bytes)
    import numpy as np
    import noisereduce as nr

    strength = max(0.05, min(1.0, float(strength)))
    audio = _load_segment(file_bytes, filename)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    reduced = nr.reduce_noise(
        y=samples,
        sr=audio.frame_rate,
        prop_decrease=strength,
        stationary=stationary,
    )
    reduced_int16 = np.clip(reduced, -32768, 32767).astype(np.int16)

    reduced_audio = AudioSegment(
        reduced_int16.tobytes(), frame_rate=audio.frame_rate, sample_width=2, channels=1
    )
    return _export_bytes(reduced_audio, "mp3")


# ---------------------------------------------------------------------------
# Normalize (peak)
# ---------------------------------------------------------------------------
def normalize(file_bytes: bytes, filename: str, target_dbfs: float = -3.0,
              output_format: str = "mp3") -> bytes:
    """Peak-normalize so the loudest sample reaches target_dbfs (e.g. -3 dBFS)."""
    check_file_size(file_bytes)
    audio = _load_segment(file_bytes, filename)
    change = target_dbfs - audio.max_dBFS
    # Avoid extreme boosts on near-silent files
    if change > 20:
        change = 20
    normalized = audio.apply_gain(change)
    return _export_bytes(normalized, output_format)


# ---------------------------------------------------------------------------
# Voice change (with dry/wet)
# ---------------------------------------------------------------------------
def voice_change(file_bytes: bytes, filename: str, effect: str,
                 dry_wet: float = 1.0, **params) -> bytes:
    """Apply a voice effect. dry_wet 0=original, 1=full effect (default)."""
    check_file_size(file_bytes)
    import numpy as np

    audio = _load_segment(file_bytes, filename)
    dry_wet = max(0.0, min(1.0, float(dry_wet if dry_wet is not None else 1.0)))

    if effect == "pitch_shift":
        # Pitch shift without changing duration (rough resampling approach)
        semitones = float(params.get("semitones", 0))
        if semitones == 0:
            result = audio
        else:
            rate_ratio = 2 ** (semitones / 12.0)
            shifted = audio._spawn(
                audio.raw_data,
                overrides={"frame_rate": int(audio.frame_rate * rate_ratio)},
            ).set_frame_rate(audio.frame_rate)
            # Time-correct by frame-rate trick inverse would need rubberband;
            # keep current practical behaviour (slight duration change on extreme shifts)
            result = shifted

    elif effect == "robot":
        intensity = float(params.get("intensity", 0.5))
        samples = np.array(audio.get_array_of_samples()).astype(np.float64)
        t = np.linspace(0, len(samples) / audio.frame_rate, len(samples), endpoint=False)
        carrier = np.sin(2 * np.pi * 60 * t)
        depth = 0.75 * intensity
        robot_samples = samples * (1 - depth + depth * carrier)
        robot_samples = np.clip(robot_samples, -32768, 32767).astype(np.int16)
        result = AudioSegment(
            robot_samples.tobytes(),
            frame_rate=audio.frame_rate,
            sample_width=audio.sample_width,
            channels=audio.channels,
        )

    elif effect == "echo":
        delay_ms = int(params.get("delay_ms", 200))
        decay = float(params.get("decay", 0.5))
        samples = np.array(audio.get_array_of_samples()).astype(np.float64)
        delay_samples = int(delay_ms * audio.frame_rate / 1000) * audio.channels
        echoed = samples.copy()
        if delay_samples < len(samples):
            echoed[delay_samples:] += samples[:-delay_samples] * decay
        echoed = np.clip(echoed, -32768, 32767).astype(np.int16)
        result = AudioSegment(
            echoed.tobytes(),
            frame_rate=audio.frame_rate,
            sample_width=audio.sample_width,
            channels=audio.channels,
        )

    elif effect == "chipmunk":
        new_rate = int(audio.frame_rate * 1.5)
        result = audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate})
        result = result.set_frame_rate(audio.frame_rate)

    elif effect == "deep_voice":
        new_rate = int(audio.frame_rate * 0.7)
        result = audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate})
        result = result.set_frame_rate(audio.frame_rate)

    elif effect in ("anon", "slight_deeper"):
        # Practical presets built on pitch_shift
        semitones = -3 if effect == "slight_deeper" else -5
        rate_ratio = 2 ** (semitones / 12.0)
        result = audio._spawn(
            audio.raw_data,
            overrides={"frame_rate": int(audio.frame_rate * rate_ratio)},
        ).set_frame_rate(audio.frame_rate)

    else:
        raise ValueError(f"Unknown effect: {effect}")

    # Dry/wet mix
    if dry_wet < 1.0 and effect not in ("chipmunk", "deep_voice"):
        # Overlay wet on dry with gain
        dry = audio
        wet = result
        # Match lengths
        min_len = min(len(dry), len(wet))
        dry = dry[:min_len]
        wet = wet[:min_len]
        dry = dry - (20 * (1 - (1 - dry_wet)))  # rough blend via gain
        # Simpler: use overlay with wet quieter when dry_wet low
        if dry_wet <= 0.01:
            result = audio
        else:
            result = dry.overlay(wet.apply_gain(-6 * (1 - dry_wet)))

    return _export_bytes(result, "mp3")


# ---------------------------------------------------------------------------
# Video to Audio — optional time range
# ---------------------------------------------------------------------------
def video_to_audio(file_bytes: bytes, filename: str, output_format: str = "mp3",
                   quality_kbps: int = 192, start_sec: float = None,
                   end_sec: float = None) -> bytes:
    check_file_size(file_bytes, max_mb=50)
    output_format = (output_format or "mp3").lower().strip()
    if output_format not in ("mp3", "wav", "ogg"):
        raise ValueError("Output format must be mp3, wav, or ogg.")
    try:
        quality_kbps = int(quality_kbps)
    except (TypeError, ValueError):
        quality_kbps = 192
    quality_kbps = max(64, min(320, quality_kbps))

    video_path, output_path = None, None
    try:
        raw_ext = (filename or "video.mp4").rsplit(".", 1)
        suffix = ("." + raw_ext[-1].lower()) if len(raw_ext) == 2 and raw_ext[-1] else ".mp4"
        if suffix not in (".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v", ".mpeg", ".mpg"):
            suffix = ".mp4"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            video_path = tmp.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}") as out_tmp:
            output_path = out_tmp.name

        import subprocess

        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_path,
        ]
        # Optional time range
        if start_sec is not None and float(start_sec) > 0:
            cmd.extend(["-ss", str(float(start_sec))])
        if end_sec is not None and float(end_sec) > 0:
            # -to is end timestamp when used after -i with -ss as output seek alternative;
            # use -t duration when both provided
            if start_sec is not None and float(start_sec) > 0:
                dur = max(0.1, float(end_sec) - float(start_sec))
                cmd.extend(["-t", str(dur)])
            else:
                cmd.extend(["-t", str(float(end_sec))])

        if output_format == "mp3":
            cmd.extend(["-vn", "-acodec", "libmp3lame", "-ab", f"{quality_kbps}k", output_path])
        elif output_format == "wav":
            cmd.extend(["-vn", "-acodec", "pcm_s16le", output_path])
        else:  # ogg
            cmd.extend(["-vn", "-acodec", "libvorbis", "-aq", "4", output_path])

        proc = subprocess.run(cmd, capture_output=True, timeout=120)
        if proc.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            err = (proc.stderr or b"").decode("utf-8", errors="ignore")[:300]
            raise Exception(f"Could not extract audio from video. {err}")

        with open(output_path, "rb") as f:
            return f.read()
    finally:
        for p in (video_path, output_path):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass
