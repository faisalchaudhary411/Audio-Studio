"""
redub_engine.py — Audio-only video redub (Phase 1 / 1.5 timed dub).

Pipeline:
  1. Extract audio from video          (ffmpeg)
  2. Google Speech in timed chunks     (free — no Whisper)
  3. Translate each segment            (Azure preferred, Google fallback)
  4. TTS each segment + place on timeline at original start times
  5. Mux new audio onto original video (ffmpeg, video stream copy)

Phase 1.5 is "timed dub" (pseudo lip-sync): speech lands in the same
windows as the source. It does not re-animate faces.
"""

from __future__ import annotations

import base64
import io
import os
import subprocess
import tempfile
import time
from typing import Optional

import requests

from errors import UserFacingError
from audio_tools import video_to_audio, check_file_size
from tts_engine import tts_dispatch

# Timed Google chunks (~12s: recognition quality vs alignment granularity)
REDUB_CHUNK_MS = 12 * 1000

# Azure Translator v3 REST
AZURE_TRANSLATE_URL = "https://api.cognitive.microsofttranslator.com/translate"

# Google Cloud Translation v2 REST (fallback only)
GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"

# Map Studio language labels → ISO codes used by Azure / Google
LANG_TO_CODE = {
    "US English": "en",
    "UK English": "en",
    "Australian": "en",
    "Indian English": "en",
    "Spanish (Spain)": "es",
    "Spanish (Mexico)": "es",
    "French": "fr",
    "French (Canada)": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese (Brazil)": "pt",
    "Portuguese (Portugal)": "pt-pt",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese (Mandarin)": "zh-Hans",
    "Arabic": "ar",
    "Hindi": "hi",
    "Urdu": "ur",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te",
    "Punjabi": "pa",
    "Turkish": "tr",
    "Russian": "ru",
    "Dutch": "nl",
    "Polish": "pl",
    "Indonesian": "id",
    "Thai": "th",
    "Vietnamese": "vi",
    "Swedish": "sv",
}

# SpeechRecognition / Whisper lang codes used by audio_tools.transcribe
TRANSCRIBE_LANGS = {
    "auto": "auto",
    "en-US": "en-US",
    "en-GB": "en-GB",
    "en-IN": "en-IN",
    "hi-IN": "hi-IN",
    "ur-PK": "ur-PK",
    "bn-IN": "bn-IN",
    "ta-IN": "ta-IN",
    "te-IN": "te-IN",
    "pa-IN": "pa-IN",
    "ar-SA": "ar-SA",
    "es-ES": "es-ES",
    "fr-FR": "fr-FR",
    "de-DE": "de-DE",
    "it-IT": "it-IT",
    "pt-BR": "pt-BR",
    "ja-JP": "ja-JP",
    "ko-KR": "ko-KR",
    "zh-CN": "zh-CN",
    "tr-TR": "tr-TR",
    "ru-RU": "ru-RU",
}

MAX_VIDEO_MB = 50
MAX_DURATION_SEC = 10 * 60  # 10 minutes hard cap for Phase 1

# Finished redub outputs live here briefly so the API can return a download
# URL instead of a multi‑MB base64 blob (huge RAM win on the 2GB VPS).
REDUB_OUT_DIR = os.environ.get("REDUB_OUT_DIR", "/tmp/voxcraft_redub_out")
REDUB_OUT_MAX_AGE_SEC = 10 * 60  # 10 minutes
os.makedirs(REDUB_OUT_DIR, exist_ok=True)


def _azure_credentials() -> tuple[str, str]:
    """Return (key, region). Region may be empty for global resources."""
    key = (os.environ.get("AZURE_TRANSLATOR_KEY") or os.environ.get("AZURE_TRANSLATE_KEY") or "").strip()
    region = (os.environ.get("AZURE_TRANSLATOR_REGION") or os.environ.get("AZURE_TRANSLATE_REGION") or "").strip()
    return key, region


def _google_api_key() -> str:
    return (os.environ.get("GOOGLE_TRANSLATE_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()


def _code_for_studio_lang(studio_lang: str) -> str:
    code = LANG_TO_CODE.get(studio_lang)
    if not code:
        raise UserFacingError(f"Target language '{studio_lang}' is not supported for redub yet.")
    return code


def _translate_azure(text: str, target_lang_code: str, source_lang_code: Optional[str] = None) -> str:
    key, region = _azure_credentials()
    if not key:
        raise UserFacingError("Azure Translator key not configured.")

    # Normalize codes Azure expects
    to_code = target_lang_code
    if to_code == "zh-CN":
        to_code = "zh-Hans"
    if to_code == "pt":
        to_code = "pt"  # Azure maps pt → Brazilian by default

    params = {"api-version": "3.0", "to": to_code}
    if source_lang_code and source_lang_code not in ("auto", ""):
        src = source_lang_code.split("-")[0].lower()
        if src == "zh":
            src = "zh-Hans"
        params["from"] = src

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json; charset=UTF-8",
    }
    if region and region.lower() not in ("global", ""):
        headers["Ocp-Apim-Subscription-Region"] = region

    body = [{"text": text}]

    try:
        resp = requests.post(AZURE_TRANSLATE_URL, params=params, headers=headers, json=body, timeout=60)
    except requests.RequestException as e:
        raise UserFacingError("Azure Translator is temporarily unreachable. Please try again in a moment.") from e

    if resp.status_code == 401:
        raise UserFacingError(
            "Azure Translator key is invalid or expired. Check AZURE_TRANSLATOR_KEY and region in the portal."
        )
    if resp.status_code == 403:
        raise UserFacingError(
            "Azure Translator access denied. Confirm the resource is active and the free/paid tier allows this call."
        )
    if resp.status_code == 429:
        raise UserFacingError("Azure Translator rate limit hit. Wait a minute and try again.")
    if resp.status_code >= 400:
        try:
            detail = resp.json()
            detail = detail[0].get("error", {}).get("message") if isinstance(detail, list) else str(detail)[:200]
        except Exception:
            detail = resp.text[:200]
        raise UserFacingError("Azure translation failed. Check the target language and try again.")

    data = resp.json()
    try:
        return data[0]["translations"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise UserFacingError("Unexpected response from Azure Translator.") from e


def _translate_google(text: str, target_lang_code: str, source_lang_code: Optional[str] = None) -> str:
    key = _google_api_key()
    if not key:
        raise UserFacingError("Google Translate key not configured.")

    # Google prefers zh-CN style
    to_code = target_lang_code
    if to_code == "zh-Hans":
        to_code = "zh-CN"
    if to_code == "pt-pt":
        to_code = "pt"

    params = {"key": key}
    body = {"q": text, "target": to_code, "format": "text"}
    if source_lang_code and source_lang_code not in ("auto", ""):
        body["source"] = source_lang_code.split("-")[0].lower()

    try:
        resp = requests.post(GOOGLE_TRANSLATE_URL, params=params, json=body, timeout=60)
    except requests.RequestException as e:
        raise UserFacingError("Google Translate is temporarily unreachable.") from e

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            detail = resp.text[:200]
        raise UserFacingError("Google translation failed. Check the target language and try again.")

    data = resp.json()
    try:
        translated = data["data"]["translations"][0]["translatedText"]
    except (KeyError, IndexError, TypeError) as e:
        raise UserFacingError("Unexpected response from Google Translate.") from e

    return (
        translated.replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .strip()
    )


def _count_sentences(text: str) -> int:
    """Rough, script-agnostic sentence count via common terminators
    (Latin/Devanagari/Gurmukhi/Urdu/CJK). Used only as a cheap signal that
    translation dropped a trailing sentence, not for anything precise."""
    import re
    if not text:
        return 0
    parts = re.split(r"[.!?۔؟।॥。]+", text)
    return len([p for p in parts if p.strip()])


def translate_text(text: str, target_lang_code: str, source_lang_code: Optional[str] = None) -> str:
    """
    Translate plain text. Prefers Azure Translator; falls back to Google if Azure
    is not configured. Set AZURE_TRANSLATOR_KEY (+ optional REGION) on the server.
    """
    text = (text or "").strip()
    if not text:
        raise UserFacingError("Nothing to translate — transcription returned empty text.")
    if len(text) > 100_000:
        raise UserFacingError("Transcript is too long to translate in one pass (100k character limit).")

    azure_key, _ = _azure_credentials()
    google_key = _google_api_key()

    if azure_key:
        return _translate_azure(text, target_lang_code, source_lang_code)
    if google_key:
        return _translate_google(text, target_lang_code, source_lang_code)

    raise UserFacingError(
        "Translation is not configured. Set AZURE_TRANSLATOR_KEY (and AZURE_TRANSLATOR_REGION if needed) "
        "on the server. Free F0 tier includes 2 million characters/month."
    )



def _probe_duration_sec(path: str) -> float:
    """Return media duration in seconds via ffprobe. 0 on failure."""
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True, timeout=30,
        )
        if proc.returncode != 0:
            return 0.0
        return float((proc.stdout or b"").decode("utf-8", errors="replace").strip() or 0)
    except Exception:
        return 0.0


def probe_video_duration(video_bytes: bytes, filename: str = "video.mp4") -> float:
    """Write bytes to a temp file and ffprobe duration. Used for early reject."""
    path = None
    try:
        raw_ext = (filename or "video.mp4").rsplit(".", 1)
        suffix = ("." + raw_ext[-1].lower()) if len(raw_ext) == 2 and raw_ext[-1] else ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(video_bytes)
            path = f.name
        return _probe_duration_sec(path)
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


def store_redub_output(data: bytes, ext: str = "mp4") -> str:
    """Persist output bytes; return a token filename for the download route."""
    import secrets
    token = f"{int(time.time())}_{secrets.token_hex(12)}.{ext.lstrip('.')}"
    path = os.path.join(REDUB_OUT_DIR, token)
    with open(path, "wb") as f:
        f.write(data)
    return token


def sweep_redub_outputs() -> None:
    """Delete redub output files older than REDUB_OUT_MAX_AGE_SEC."""
    cutoff = time.time() - REDUB_OUT_MAX_AGE_SEC
    try:
        for name in os.listdir(REDUB_OUT_DIR):
            path = os.path.join(REDUB_OUT_DIR, name)
            try:
                if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                    os.unlink(path)
            except OSError:
                pass
    except OSError:
        pass


def _atempo_chain(ratio: float) -> str:
    """Build an atempo filter chain. Each atempo stage must be in [0.5, 2.0]."""
    if ratio <= 0:
        return "atempo=1.0"
    stages = []
    r = float(ratio)
    # Speed up: ratio > 1 means play faster (shorter output). atempo = ratio.
    # We receive stretch_factor = target/tts so atempo = tts/target = 1/stretch when matching length.
    # Caller passes the atempo value directly (playback speed).
    while r > 2.0 + 1e-6:
        stages.append(2.0)
        r /= 2.0
    while r < 0.5 - 1e-6:
        stages.append(0.5)
        r /= 0.5
    stages.append(max(0.5, min(2.0, r)))
    return ",".join(f"atempo={s:.6f}" for s in stages)


def stretch_audio_to_duration(audio_bytes: bytes, target_sec: float, audio_ext: str = "mp3") -> bytes:
    """
    Pitch-preserving time-stretch so output duration ≈ target_sec.
    Uses ffmpeg atempo. If durations are already close (<3% diff), returns input unchanged.
    Extreme ratios are clamped to keep speech intelligible (~0.5x–2x effective after chaining).
    """
    if not audio_bytes or target_sec <= 0.05:
        return audio_bytes

    in_path = out_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_ext}") as f:
            f.write(audio_bytes)
            in_path = f.name
        src_dur = _probe_duration_sec(in_path)
        if src_dur <= 0.05:
            return audio_bytes

        # atempo = src/target → output duration = src / atempo ≈ target
        ratio = src_dur / target_sec
        if abs(ratio - 1.0) < 0.03:
            return audio_bytes  # already close enough

        # Soft clamp: don't make speech unintelligible. Widened slightly
        # from the original 0.5-2.0 for redub specifically (see the
        # coverage/gap reporting added in redub_video() below — pushing
        # the clamp further than this starts costing more intelligibility
        # than it buys in extra coverage, so past this point we report the
        # remaining gap instead of trying to out-stretch it).
        ratio = max(0.45, min(2.2, ratio))
        # Allow chaining beyond single-stage limits for moderate extremes already clamped
        filt = _atempo_chain(ratio)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            out_path = f.name

        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", in_path,
            "-filter:a", filt,
            "-c:a", "libmp3lame", "-b:a", "192k",
            out_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=120)
        if proc.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) < 100:
            # Fall back to original rather than failing the whole job
            return audio_bytes
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        for path in (in_path, out_path):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass


def mux_audio_onto_video(video_bytes: bytes, video_filename: str, audio_bytes: bytes,
                         audio_ext: str = "mp3", *, match_video_length: bool = True) -> bytes:
    """Replace the video's audio track with new audio. Video stream is stream-copied.

    If match_video_length is True (default after Phase 1.5), audio is padded with silence
    or trimmed so the output video keeps the original picture duration.
    If False, uses -shortest (legacy behaviour).
    """
    video_path = audio_path = out_path = None
    try:
        raw_ext = (video_filename or "video.mp4").rsplit(".", 1)
        v_suffix = ("." + raw_ext[-1].lower()) if len(raw_ext) == 2 and raw_ext[-1] else ".mp4"
        if v_suffix not in (".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v", ".mpeg", ".mpg"):
            v_suffix = ".mp4"

        with tempfile.NamedTemporaryFile(delete=False, suffix=v_suffix) as vt:
            vt.write(video_bytes)
            video_path = vt.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_ext}") as at:
            at.write(audio_bytes)
            audio_path = at.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as ot:
            out_path = ot.name

        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
        ]
        if match_video_length:
            # Keep full video length; pad audio with silence if short, trim if long
            cmd += ["-af", "apad", "-shortest"]
        else:
            cmd += ["-shortest"]
        cmd.append(out_path)

        proc = subprocess.run(cmd, capture_output=True, timeout=180)
        if proc.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) < 100:
            # Do not forward raw ffmpeg stderr (paths, codecs) to clients
            raise UserFacingError("Could not mux audio onto video. Try a different file format (MP4 works best).")

        with open(out_path, "rb") as f:
            return f.read()
    finally:
        for p in (video_path, audio_path, out_path):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass


def google_transcribe_segments(
    audio_bytes: bytes,
    filename: str = "extracted.mp3",
    lang_code: str = "auto",
    chunk_ms: int = REDUB_CHUNK_MS,
) -> list[dict]:
    """Transcribe with Google Speech in fixed time windows.

    Returns list of {start_sec, end_sec, text}. Empty/failed windows are
    omitted (timeline keeps silence there). No Whisper — Google only.
    """
    import speech_recognition as sr
    from pydub import AudioSegment

    google_lang = (
        lang_code
        if lang_code and str(lang_code).lower() not in ("auto", "none", "detect", "")
        else "ur-PK"
    )
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes)).set_frame_rate(16000).set_channels(1)
    duration_sec = len(audio) / 1000.0
    chunk_ms = max(4000, min(30000, int(chunk_ms or REDUB_CHUNK_MS)))
    total_chunks = max(1, (len(audio) + chunk_ms - 1) // chunk_ms)

    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.operation_timeout = 25

    segments: list[dict] = []
    for ci in range(total_chunks):
        start_ms = ci * chunk_ms
        end_ms = min(len(audio), (ci + 1) * chunk_ms)
        if end_ms - start_ms < 400:
            continue
        chunk = audio[start_ms:end_ms]
        chunk_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                chunk.export(tmp.name, format="wav")
                chunk_path = tmp.name
            with sr.AudioFile(chunk_path) as source:
                r.adjust_for_ambient_noise(source, duration=min(0.4, len(chunk) / 1000))
                audio_data = r.record(source)
            text = ""
            try:
                text = r.recognize_google(audio_data, language=google_lang)
            except sr.UnknownValueError:
                text = ""
            except Exception:
                time.sleep(0.8)
                try:
                    text = r.recognize_google(audio_data, language=google_lang)
                except Exception:
                    text = ""
            text = (text or "").strip()
            if text:
                segments.append({
                    "start_sec": round(start_ms / 1000.0, 3),
                    "end_sec": round(end_ms / 1000.0, 3),
                    "text": text,
                })
        finally:
            if chunk_path and os.path.exists(chunk_path):
                try:
                    os.unlink(chunk_path)
                except OSError:
                    pass

    if not segments:
        raise UserFacingError(
            "Could not detect speech in this video. Try a clearer audio track, "
            "or set the source language manually instead of Auto."
        )
    # Attach total duration for callers
    for s in segments:
        s["_total_duration_sec"] = duration_sec
    return segments


def assemble_timed_dub(
    segment_audio: list[tuple[float, float, bytes]],
    total_duration_sec: float,
) -> bytes:
    """Build one MP3 timeline: place each TTS clip at start_sec, stretched to fit window.

    segment_audio: list of (start_sec, end_sec, mp3_bytes)
    """
    from pydub import AudioSegment

    total_ms = max(1000, int(float(total_duration_sec) * 1000))
    timeline = AudioSegment.silent(duration=total_ms, frame_rate=24000)

    for start_sec, end_sec, mp3_bytes in segment_audio:
        if not mp3_bytes:
            continue
        start_ms = max(0, int(float(start_sec) * 1000))
        end_ms = max(start_ms + 200, int(float(end_sec) * 1000))
        window_sec = max(0.25, (end_ms - start_ms) / 1000.0)
        fitted = stretch_audio_to_duration(mp3_bytes, window_sec, audio_ext="mp3")
        try:
            clip = AudioSegment.from_file(io.BytesIO(fitted), format="mp3")
        except Exception:
            continue
        # Don't overflow the timeline
        if start_ms >= total_ms:
            continue
        max_len = total_ms - start_ms
        if len(clip) > max_len:
            clip = clip[:max_len]
        timeline = timeline.overlay(clip, position=start_ms)

    buf = io.BytesIO()
    timeline.export(buf, format="mp3", bitrate="192k")
    return buf.getvalue()


def redub_video(
    video_bytes: bytes,
    filename: str,
    *,
    source_lang: str = "auto",
    target_studio_lang: str = "US English",
    voice_id: str = "en-US-JennyNeural",
    speed_pct: int = 100,
    match_length: bool = True,
) -> dict:
    """
    Full redub pipeline. Returns dict with download tokens (not base64) for
    video/audio, plus transcript metadata.
    """
    check_file_size(video_bytes, max_mb=MAX_VIDEO_MB)
    sweep_redub_outputs()

    # Early duration reject — before extract/transcribe/TTS burn CPU
    probed = probe_video_duration(video_bytes, filename)
    if probed and probed > MAX_DURATION_SEC:
        raise UserFacingError(
            f"Video is about {int(probed // 60)} minutes — Phase 1 redub supports up to "
            f"{MAX_DURATION_SEC // 60} minutes. Trim the video first, or wait for longer limits."
        )

    source_lang = (source_lang or "auto").strip()
    if source_lang not in TRANSCRIBE_LANGS:
        source_lang = "auto"

    # ---- 1. Extract audio ----
    audio_bytes = video_to_audio(video_bytes, filename, output_format="mp3", quality_kbps=192)

    # Prefer accurate duration from extracted audio
    original_dur = float(probed or 0)
    tmp_a = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(audio_bytes)
            tmp_a = f.name
        d = _probe_duration_sec(tmp_a)
        if d > 0.05:
            original_dur = d
    finally:
        if tmp_a:
            try:
                os.unlink(tmp_a)
            except OSError:
                pass
    if original_dur and original_dur > MAX_DURATION_SEC:
        raise UserFacingError(
            f"Video is about {int(original_dur // 60)} minutes — Phase 1 redub supports up to "
            f"{MAX_DURATION_SEC // 60} minutes. Trim the video first, or wait for longer limits."
        )

    # ---- 2. Google Speech in timed chunks (no Whisper) ----
    segments = google_transcribe_segments(audio_bytes, "extracted.mp3", source_lang)
    if segments and segments[0].get("_total_duration_sec"):
        original_dur = float(segments[0]["_total_duration_sec"]) or original_dur
    transcript = " ".join(s["text"] for s in segments).strip()

    # ---- 3. Translate each segment ----
    target_code = _code_for_studio_lang(target_studio_lang)
    source_code = None
    if source_lang != "auto":
        source_code = source_lang.split("-")[0].lower()
        if source_code == "zh":
            source_code = "zh-Hans"

    same_lang = False
    if source_code and source_code.split("-")[0] == target_code.split("-")[0]:
        same_lang = True

    translation_note = None
    translated_parts: list[str] = []
    for seg in segments:
        src = seg["text"]
        if same_lang:
            seg["translated"] = src
        else:
            try:
                seg["translated"] = translate_text(src, target_code, source_lang_code=source_code)
            except UserFacingError:
                seg["translated"] = ""
        if not (seg.get("translated") or "").strip():
            # Keep window silent rather than failing the whole job
            seg["translated"] = ""
        else:
            translated_parts.append(seg["translated"].strip())

    translated = " ".join(translated_parts).strip()
    if not translated:
        raise UserFacingError("Translation returned empty text for every segment.")

    if not same_lang:
        src_sentences = _count_sentences(transcript)
        tgt_sentences = _count_sentences(translated)
        if src_sentences >= 2 and tgt_sentences < src_sentences * 0.6:
            translation_note = (
                "The translation may be missing part of the original speech "
                f"(source ~{src_sentences} sentences, translation ~{tgt_sentences}). "
                "Check the transcript below and try again if something important is missing."
            )

    # ---- 4. TTS per segment + place on timeline (timed dub) ----
    speed_pct = max(50, min(200, int(speed_pct or 100)))
    rate_str = f"{speed_pct - 100:+d}%"
    tts_meta: dict = {}
    voice_note = None
    timed_clips: list[tuple[float, float, bytes]] = []
    tts_failures = 0

    for seg in segments:
        text = (seg.get("translated") or "").strip()
        if not text:
            continue
        meta: dict = {}
        clip = tts_dispatch(
            text, voice_id, rate=rate_str, ssml_mode=False, speed_pct=speed_pct, _meta=meta
        )
        if not clip:
            tts_failures += 1
            continue
        if meta.get("engine") == "gtts_fallback":
            voice_note = (
                "Your selected voice was temporarily unavailable for some segments, "
                "so a substitute voice was used (gender/accent may differ)."
            )
        # Optionally skip strict window fitting when match_length is off:
        # still place at start, but use natural TTS length (may overlap next)
        end = seg["end_sec"] if match_length else (seg["start_sec"] + max(0.5, (seg["end_sec"] - seg["start_sec"])))
        timed_clips.append((seg["start_sec"], end, clip))
        if not tts_meta:
            tts_meta.update(meta)

    if not timed_clips:
        raise UserFacingError("Could not generate the dubbed voice track. Try another voice.")

    total_dur = original_dur if original_dur > 0.05 else max(s["end_sec"] for s in segments)
    tts_audio = assemble_timed_dub(timed_clips, total_dur)
    if not tts_audio:
        raise UserFacingError("Could not assemble the dubbed audio timeline.")

    stretched = True  # per-segment fit
    stretch_ratio = 1.0
    tts_dur_final = total_dur
    silent_tail_sec = 0.0
    trimmed_sec = 0.0
    length_note = (
        f"Timed dub: {len(timed_clips)} speech window(s) aligned to the original timeline "
        f"using Google Speech chunks (~{REDUB_CHUNK_MS // 1000}s). "
        "This is audio alignment only — faces are not re-animated."
    )
    if tts_failures:
        length_note += f" {tts_failures} segment(s) failed TTS and were left silent."

    # ---- 5. Mux ----
    dubbed_video = mux_audio_onto_video(
        video_bytes, filename, tts_audio, audio_ext="mp3", match_video_length=bool(match_length),
    )

    ts = time.time()
    out_name = f"VoxCraft-Redub-{int(ts)}.mp4"
    audio_name = f"VoxCraft-Redub-Audio-{int(ts)}.mp3"

    # Store on disk — avoid returning multi‑MB base64 in the JSON response
    video_token = store_redub_output(dubbed_video, "mp4")
    audio_token = store_redub_output(tts_audio, "mp3")

    return {
        "video_token": video_token,
        "audio_token": audio_token,
        "download_video_url": f"/api/tools/redub/download/{video_token}",
        "download_audio_url": f"/api/tools/redub/download/{audio_token}",
        "filename": out_name,
        "audio_filename": audio_name,
        "transcript": transcript,
        "translated": translated,
        "char_count": len(translated),
        "size_kb": round(len(dubbed_video) / 1024, 1),
        "audio_size_kb": round(len(tts_audio) / 1024, 1),
        "skipped_translation": same_lang,
        "target_lang": target_studio_lang,
        "voice_id": voice_id,
        "match_length": bool(match_length),
        "original_duration_sec": round(original_dur, 2) if original_dur else None,
        "length_matched": bool(match_length and original_dur > 0.05),
        "silent_tail_sec": silent_tail_sec,
        "trimmed_sec": trimmed_sec,
        "length_note": length_note,
        "voice_note": voice_note,
        "translation_note": translation_note,
        "timed_segments": len(timed_clips),
        "engine": "google_timed",
    }
