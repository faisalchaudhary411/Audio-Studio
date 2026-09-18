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
import re
import subprocess
import tempfile
import time
from typing import Optional

import requests

from errors import UserFacingError
from audio_tools import video_to_audio, check_file_size
from tts_engine import tts_dispatch

try:
    import modal_whisper
except ImportError:  # pragma: no cover
    modal_whisper = None  # type: ignore

# Fallback fixed-window when silence detection finds too few cuts.
# Keep short so dialogue turns don't mash into one TTS blob.
REDUB_CHUNK_MS = 5 * 1000
REDUB_MAX_SEG_MS = 8 * 1000
REDUB_MIN_SEG_MS = 700
# Gentle stretch — extreme atempo made sample redubs unintelligible
REDUB_STRETCH_MIN = 0.78
REDUB_STRETCH_MAX = 1.28
# If TTS is shorter than the window, leave trailing silence instead of
# stretching more than this factor (sounds more natural for dialogue).
REDUB_PAD_INSTEAD_OF_STRETCH = 1.18

# --- Hinglish / Indian-number glossary (Google-only quality aids) ---
# Applied after ASR and after translation. Order matters for some patterns.
_ASR_FIXES = [
    # Common Google ASR garbling on short Hindi/Hinglish clips
    (r"\bbetay\b", "bete"),
    (r"\bklye\b", "ke liye"),
    (r"\bkia\b", "kya"),
    (r"\bhojaingi\b", "ho jayegi"),
    (r"\bhojayegi\b", "ho jayegi"),
    (r"\bmehnga\b", "mehnga"),
    (r"\bmehanga\b", "mehnga"),
    (r"\bbilkul banega\b", "bilkul banega"),
    (r"\bbilkul ban jayega\b", "bilkul ban jayega"),
    (r"\bspecs dkhat[e]?\b", "specs dekhte"),
    (r"\bdkhate\b", "dekhte"),
    (r"\bbna denge\b", "bana denge"),
    (r"\brs\.?\s*11[,.]?40+0*\b", "Rs 11,40,000", re.I),
    (r"\b11\s*lakh\s*4(?:0+)?\b", "11 lakh 40 thousand", re.I),
    (r"\bc\s*b\s*s\s*e\b", "CBSE", re.I),
]

_TRANSLATE_GLOSSARY = [
    # Indian number words → clear English for TTS
    (r"\b(\d+)\s*lakh(?:s)?\b", r"\1 lakh", re.I),
    (r"\b(\d+)\s*crore(?:s)?\b", r"\1 crore", re.I),
    (r"\beleven\s+lakh\s+four\b", "eleven lakh forty thousand", re.I),
    (r"\beleven\s+lakh\s+4\b", "eleven lakh forty thousand", re.I),
    (r"\b11\s*,?\s*40+0*\b", "11,40,000"),
    (r"\brs\.?\s*11[,.]?40+0*\b", "1,140,000 rupees", re.I),
    (r"\b1[,.]?140[,.]?000\b", "1,140,000"),
    # Keep hardware terms readable for TTS
    (r"\brtx\s*5080\b", "RTX 5080", re.I),
    (r"\bi9\s*14(?:th)?\s*gen\b", "i9 14th gen", re.I),
    (r"\b32\s*gb\s*ram\b", "32 GB RAM", re.I),
    (r"\b1\s*tb\s*ssd\b", "1 TB SSD", re.I),
    (r"\bmicrosoft\s+word\b", "Microsoft Word", re.I),
    # Soften awkward literal translations common on this content
    (r"\bit will be done at all\b", "absolutely, it can be done", re.I),
    (r"\byes,?\s*it will be done at all\b", "Yes, absolutely, it can be done", re.I),
    (r"\bneed a system what is the condition for me\b",
     "for running Microsoft Word you need a decent system, right", re.I),
]


def _apply_pattern_list(text: str, patterns: list) -> str:
    if not text:
        return text
    out = text
    for item in patterns:
        if len(item) == 3:
            pat, repl, flags = item
            out = re.sub(pat, repl, out, flags=flags)
        else:
            pat, repl = item
            out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out


def clean_asr_text(text: str) -> str:
    """Light cleanup of Google ASR output (Hinglish typos, clipped words)."""
    text = (text or "").strip()
    if not text:
        return ""
    text = _apply_pattern_list(text, _ASR_FIXES)
    # Collapse repeated spaces / odd punctuation from ASR
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    return text


def postprocess_translation(text: str) -> str:
    """Fix numbers, lakh/crore, and common bad literal translations before TTS."""
    text = (text or "").strip()
    if not text:
        return ""
    text = _apply_pattern_list(text, _TRANSLATE_GLOSSARY)
    # "eleven lakh four I" style garbage → try to salvage
    text = re.sub(
        r"\b(eleven|11)\s+lakh\s+four\s*[a-z]?\b",
        "eleven lakh forty thousand",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text

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
    is not configured. Always runs postprocess_translation for numbers / Hinglish.
    """
    text = (text or "").strip()
    if not text:
        raise UserFacingError("Nothing to translate — transcription returned empty text.")
    if len(text) > 100_000:
        raise UserFacingError("Transcript is too long to translate in one pass (100k character limit).")

    azure_key, _ = _azure_credentials()
    google_key = _google_api_key()

    if azure_key:
        out = _translate_azure(text, target_lang_code, source_lang_code)
    elif google_key:
        out = _translate_google(text, target_lang_code, source_lang_code)
    else:
        raise UserFacingError(
            "Translation is not configured. Set AZURE_TRANSLATOR_KEY (and AZURE_TRANSLATOR_REGION if needed) "
            "on the server. Free F0 tier includes 2 million characters/month."
        )
    return postprocess_translation(out)



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


def stretch_audio_to_duration(
    audio_bytes: bytes,
    target_sec: float,
    audio_ext: str = "mp3",
    *,
    min_ratio: float = None,
    max_ratio: float = None,
) -> bytes:
    """
    Pitch-preserving time-stretch so output duration ≈ target_sec.
    Uses ffmpeg atempo. If durations are already close (<3% diff), returns input unchanged.
    Ratios clamped for intelligibility (redub uses gentler defaults via kwargs).
    """
    if not audio_bytes or target_sec <= 0.05:
        return audio_bytes

    lo = REDUB_STRETCH_MIN if min_ratio is None else float(min_ratio)
    hi = REDUB_STRETCH_MAX if max_ratio is None else float(max_ratio)

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

        ratio = max(lo, min(hi, ratio))
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


def _segment_windows_ms(audio) -> list[tuple[int, int]]:
    """Build (start_ms, end_ms) speech windows via silence detection, else fixed chunks.

    Silence cuts track dialogue turns much better than fixed 12s blocks
    (which mashed multiple speakers into one bad TTS blob on short reels).
    """
    from pydub.silence import detect_nonsilent

    duration_ms = len(audio)
    thresh = max(-42, int(audio.dBFS) - 14) if audio.dBFS != float("-inf") else -35
    try:
        nonsilent = detect_nonsilent(
            audio,
            min_silence_len=280,
            silence_thresh=thresh,
            seek_step=15,
        )
    except Exception:
        nonsilent = []

    windows: list[tuple[int, int]] = []
    if nonsilent and len(nonsilent) >= 2:
        for start, end in nonsilent:
            if end - start < REDUB_MIN_SEG_MS:
                continue
            # Split long runs so one window ≈ one short utterance
            pos = start
            while pos < end:
                chunk_end = min(end, pos + REDUB_MAX_SEG_MS)
                if chunk_end - pos >= REDUB_MIN_SEG_MS:
                    windows.append((pos, chunk_end))
                pos = chunk_end
        # Merge tiny gaps (<350ms) between adjacent windows of same speaker rush
        merged: list[tuple[int, int]] = []
        for s, e in windows:
            if merged and s - merged[-1][1] < 350 and (e - merged[-1][0]) <= REDUB_MAX_SEG_MS + 500:
                merged[-1] = (merged[-1][0], e)
            else:
                merged.append((s, e))
        windows = merged

    if len(windows) < 2:
        # Fixed short windows as fallback
        chunk_ms = REDUB_CHUNK_MS
        windows = []
        pos = 0
        while pos < duration_ms:
            end = min(duration_ms, pos + chunk_ms)
            if end - pos >= REDUB_MIN_SEG_MS:
                windows.append((pos, end))
            pos = end

    return windows


def _google_recognize_chunk(r, chunk, google_lang: str) -> str:
    import speech_recognition as sr

    chunk_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            chunk.export(tmp.name, format="wav")
            chunk_path = tmp.name
        with sr.AudioFile(chunk_path) as source:
            r.adjust_for_ambient_noise(source, duration=min(0.35, len(chunk) / 1000))
            audio_data = r.record(source)
        try:
            return (r.recognize_google(audio_data, language=google_lang) or "").strip()
        except sr.UnknownValueError:
            return ""
        except Exception:
            time.sleep(0.7)
            try:
                return (r.recognize_google(audio_data, language=google_lang) or "").strip()
            except Exception:
                return ""
    finally:
        if chunk_path and os.path.exists(chunk_path):
            try:
                os.unlink(chunk_path)
            except OSError:
                pass


def whisper_transcribe_segments(
    audio_bytes: bytes,
    lang_code: str = "auto",
    *,
    timeout_sec: float = 120.0,
) -> list[dict]:
    """Transcribe via Modal faster-whisper; return timed segments.

    Uses Whisper's own VAD segment boundaries (much better than fixed chunks
    for dialogue). Falls back to raising so the caller can try Google.
    """
    if modal_whisper is None or not modal_whisper.is_configured():
        raise UserFacingError("Whisper is not configured on this server.")

    whisper_lang = None
    if lang_code and str(lang_code).lower() not in ("auto", "none", "detect", ""):
        whisper_lang = str(lang_code).strip().lower().split("-")[0]

    # Domain hint helps numbers / hardware terms on short Hinglish reels
    prompt = (
        "Hindi and Hinglish conversation in a computer shop. "
        "PC parts: RTX 5080, Intel i9 14th Gen, 32 GB RAM, 1 TB SSD. "
        "Prices in Indian rupees and lakhs."
    )

    result = modal_whisper.transcribe_audio(
        audio_bytes,
        language=whisper_lang,
        task="transcribe",
        model_size="large-v3",
        word_timestamps=False,
        vad_filter=True,
        initial_prompt=prompt,
        timeout_sec=timeout_sec,
        max_retries=1,
    )
    if not result.get("success"):
        err = (result.get("error") or "Whisper failed").strip()[:180]
        raise UserFacingError(f"Whisper transcription failed: {err}")

    raw_segs = result.get("segments") or []
    duration_sec = float(result.get("duration_sec") or 0.0)
    segments: list[dict] = []
    for s in raw_segs:
        text = clean_asr_text((s.get("text") or "").strip())
        if not text:
            continue
        start = float(s.get("start") or 0.0)
        end = float(s.get("end") or start)
        if end - start < 0.25:
            end = start + 0.4
        segments.append({
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "text": text,
        })

    if not segments:
        # Whole-file text only — single window
        text = clean_asr_text((result.get("text") or "").strip())
        if not text:
            raise UserFacingError("Whisper returned empty speech.")
        if duration_sec <= 0.05:
            duration_sec = max(1.0, end if segments else 5.0)
        segments = [{
            "start_sec": 0.0,
            "end_sec": round(duration_sec, 3),
            "text": text,
        }]

    if duration_sec <= 0.05 and segments:
        duration_sec = float(segments[-1]["end_sec"])
    for s in segments:
        s["_total_duration_sec"] = duration_sec
        s["_engine"] = "whisper"
    return segments


def google_transcribe_segments(
    audio_bytes: bytes,
    filename: str = "extracted.mp3",
    lang_code: str = "auto",
    chunk_ms: int = REDUB_CHUNK_MS,
) -> list[dict]:
    """Transcribe with Google Speech on silence-based (or short fixed) windows.

    Returns list of {start_sec, end_sec, text}. Empty windows omitted.
    Used as fallback when Whisper is unavailable or fails.
    """
    import speech_recognition as sr
    from pydub import AudioSegment

    google_lang = (
        lang_code
        if lang_code and str(lang_code).lower() not in ("auto", "none", "detect", "")
        else "hi-IN"  # Hindi-first for typical short-form source; UI can override
    )
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes)).set_frame_rate(16000).set_channels(1)
    duration_sec = len(audio) / 1000.0
    windows = _segment_windows_ms(audio)

    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.operation_timeout = 25

    segments: list[dict] = []
    for start_ms, end_ms in windows:
        # Small pad so word edges aren't clipped
        pad = 80
        s = max(0, start_ms - pad)
        e = min(len(audio), end_ms + pad)
        if e - s < REDUB_MIN_SEG_MS:
            continue
        text = clean_asr_text(_google_recognize_chunk(r, audio[s:e], google_lang))
        if text:
            segments.append({
                "start_sec": round(start_ms / 1000.0, 3),
                "end_sec": round(end_ms / 1000.0, 3),
                "text": text,
            })

    if not segments:
        raise UserFacingError(
            "Could not detect speech in this video. Try a clearer audio track, "
            "or set the source language manually instead of Auto."
        )
    for s in segments:
        s["_total_duration_sec"] = duration_sec
    return segments


def assemble_timed_dub(
    segment_audio: list[tuple[float, float, bytes]],
    total_duration_sec: float,
) -> bytes:
    """Build one MP3 timeline: place each TTS clip at start_sec.

    Prefer natural TTS length + trailing silence inside the window when the
    clip is shorter than the original speech. Only stretch when the clip is
    longer than the window (or mildly shorter within REDUB_PAD_INSTEAD_OF_STRETCH).
    This keeps dialogue gaps and avoids robotic slow-speech.
    """
    from pydub import AudioSegment

    total_ms = max(1000, int(float(total_duration_sec) * 1000))
    timeline = AudioSegment.silent(duration=total_ms, frame_rate=24000)

    for start_sec, end_sec, mp3_bytes in segment_audio:
        if not mp3_bytes:
            continue
        start_ms = max(0, int(float(start_sec) * 1000))
        end_ms = max(start_ms + 200, int(float(end_sec) * 1000))
        window_ms = end_ms - start_ms
        window_sec = max(0.25, window_ms / 1000.0)

        try:
            raw = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
        except Exception:
            continue
        tts_ms = len(raw)
        if tts_ms < 80:
            continue

        # Decide stretch vs pad:
        # - TTS longer than window → speed up (clamp) to fit
        # - TTS much shorter → leave natural length + silence (no slow-mo)
        # - mild shortfall → gentle stretch only
        if tts_ms > window_ms:
            fitted = stretch_audio_to_duration(mp3_bytes, window_sec, audio_ext="mp3")
            try:
                clip = AudioSegment.from_file(io.BytesIO(fitted), format="mp3")
            except Exception:
                clip = raw[:window_ms]
        elif tts_ms * REDUB_PAD_INSTEAD_OF_STRETCH < window_ms:
            # Keep natural pace; silence fills the rest of the dialogue gap
            clip = raw
        else:
            fitted = stretch_audio_to_duration(mp3_bytes, window_sec, audio_ext="mp3")
            try:
                clip = AudioSegment.from_file(io.BytesIO(fitted), format="mp3")
            except Exception:
                clip = raw

        if start_ms >= total_ms:
            continue
        max_len = total_ms - start_ms
        if len(clip) > max_len:
            clip = clip[:max_len]
        # Also never spill past this segment's original end by more than 120ms
        hard_cap = min(max_len, window_ms + 120)
        if len(clip) > hard_cap:
            clip = clip[:hard_cap]
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
    voice_id_b: Optional[str] = None,
    speed_pct: int = 100,
    match_length: bool = True,
    asr_engine: str = "auto",
) -> dict:
    """
    Full redub pipeline. Returns dict with download tokens (not base64) for
    video/audio, plus transcript metadata.

    voice_id_b: optional second stock voice. When set, segments alternate
    voice_id / voice_id_b (cheap two-speaker approximation, no diarization).

    asr_engine: "auto" | "whisper" | "google"
      - auto: Whisper first (if configured), Google fallback
      - whisper: Whisper only (error if unavailable)
      - google: Google only (previous behaviour)
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
    voice_id_b = (voice_id_b or "").strip() or None

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

    # ---- 2. Transcribe timed segments (Whisper preferred, Google fallback) ----
    asr_engine = (asr_engine or "auto").strip().lower()
    if asr_engine not in ("auto", "whisper", "google"):
        asr_engine = "auto"

    segments: list[dict] = []
    used_engine = "google"
    asr_note = None

    def _try_whisper() -> list[dict]:
        return whisper_transcribe_segments(audio_bytes, source_lang, timeout_sec=150.0)

    def _try_google() -> list[dict]:
        return google_transcribe_segments(audio_bytes, "extracted.mp3", source_lang)

    if asr_engine == "google":
        segments = _try_google()
        used_engine = "google"
    elif asr_engine == "whisper":
        segments = _try_whisper()
        used_engine = "whisper"
    else:
        # auto: Whisper first when Modal endpoint is set
        whisper_ok = (
            modal_whisper is not None
            and modal_whisper.is_configured()
        )
        if whisper_ok:
            try:
                segments = _try_whisper()
                used_engine = "whisper"
            except Exception as e:
                asr_note = f"Whisper unavailable ({str(e)[:120]}); used Google Speech."
                print(f"[redub] Whisper failed, Google fallback: {e}", flush=True)
                segments = _try_google()
                used_engine = "google"
        else:
            segments = _try_google()
            used_engine = "google"
            asr_note = "Whisper not configured — using Google Speech."

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
            # Still run number / Hinglish cleanup even when not translating
            seg["translated"] = postprocess_translation(src) or src
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
    dual_voice = bool(voice_id_b and voice_id_b != voice_id)
    spoken_idx = 0

    for seg in segments:
        text = (seg.get("translated") or "").strip()
        if not text:
            continue
        # Alternate voices for a cheap two-speaker effect (no diarization)
        use_voice = voice_id
        if dual_voice:
            use_voice = voice_id if (spoken_idx % 2 == 0) else voice_id_b
        spoken_idx += 1

        meta: dict = {}
        clip = tts_dispatch(
            text, use_voice, rate=rate_str, ssml_mode=False, speed_pct=speed_pct, _meta=meta
        )
        if not clip:
            tts_failures += 1
            continue
        if meta.get("engine") == "gtts_fallback":
            voice_note = (
                "Your selected voice was temporarily unavailable for some segments, "
                "so a substitute voice was used (gender/accent may differ)."
            )
        end = seg["end_sec"] if match_length else (
            seg["start_sec"] + max(0.5, (seg["end_sec"] - seg["start_sec"]))
        )
        timed_clips.append((seg["start_sec"], end, clip))
        if not tts_meta:
            tts_meta.update(meta)

    if not timed_clips:
        raise UserFacingError("Could not generate the dubbed voice track. Try another voice.")

    total_dur = original_dur if original_dur > 0.05 else max(s["end_sec"] for s in segments)
    tts_audio = assemble_timed_dub(timed_clips, total_dur)
    if not tts_audio:
        raise UserFacingError("Could not assemble the dubbed audio timeline.")

    stretched = True  # per-segment fit where needed
    stretch_ratio = 1.0
    tts_dur_final = total_dur
    silent_tail_sec = 0.0
    trimmed_sec = 0.0
    asr_label = "Whisper (GPU)" if used_engine == "whisper" else "Google Speech"
    length_note = (
        f"Timed dub: {len(timed_clips)} speech window(s) via {asr_label}. "
        "Natural pace preferred; light stretch only when a line overruns its window. "
        "Numbers and common Hinglish terms are cleaned before TTS. "
        "Faces are not re-animated. Set source language to Hindi (hi-IN) for best results on Indian clips."
    )
    if asr_note:
        length_note += f" {asr_note}"
    if dual_voice:
        length_note += f" Two voices alternated by segment ({voice_id} / {voice_id_b})."
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
        "voice_id_b": voice_id_b if dual_voice else None,
        "match_length": bool(match_length),
        "original_duration_sec": round(original_dur, 2) if original_dur else None,
        "length_matched": bool(match_length and original_dur > 0.05),
        "silent_tail_sec": silent_tail_sec,
        "trimmed_sec": trimmed_sec,
        "length_note": length_note,
        "voice_note": voice_note,
        "translation_note": translation_note,
        "timed_segments": len(timed_clips),
        "engine": f"{used_engine}_timed",
        "asr_engine": used_engine,
        "dual_voice": dual_voice,
    }
