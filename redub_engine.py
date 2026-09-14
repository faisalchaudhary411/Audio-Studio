"""
redub_engine.py — Audio-only video redub (Phase 1).

Pipeline (all local / free except Google Translate):
  1. Extract audio from video          (ffmpeg — already paid for on VPS)
  2. Transcribe original audio         (existing audio_tools.transcribe)
  3. Translate transcript              (Google Cloud Translation NMT)
  4. Re-voice with edge-tts stock voice (existing tts_engine.tts_dispatch)
  5. Mux new audio onto original video (ffmpeg)

No GPU / no voice cloning. Gated to Pro (not Pro+) in the API layer.
"""

from __future__ import annotations

import base64
import os
import subprocess
import tempfile
from typing import Optional

import requests

from errors import UserFacingError
from audio_tools import video_to_audio, transcribe, check_file_size
from tts_engine import tts_dispatch

# Google Cloud Translation v2 REST (basic NMT). Free tier: 500K chars/month.
GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"

# Map Studio language labels → Google Translate language codes.
# Only languages we actually ship voices for need entries.
LANG_TO_GOOGLE = {
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
    "Portuguese (Portugal)": "pt",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese (Mandarin)": "zh-CN",
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
    "Polish": "pl",
    "Dutch": "nl",
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


def _google_api_key() -> str:
    key = (os.environ.get("GOOGLE_TRANSLATE_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not key:
        raise UserFacingError(
            "Translation is not configured yet. Set GOOGLE_TRANSLATE_API_KEY on the server "
            "(Google Cloud Translation free tier covers ~110 five-minute jobs/month)."
        )
    return key


def translate_text(text: str, target_lang_code: str, source_lang_code: Optional[str] = None) -> str:
    """Translate plain text via Google Cloud Translation NMT v2 REST."""
    text = (text or "").strip()
    if not text:
        raise UserFacingError("Nothing to translate — transcription returned empty text.")
    if len(text) > 100_000:
        raise UserFacingError("Transcript is too long to translate in one pass (100k character limit).")

    params = {"key": _google_api_key()}
    body = {
        "q": text,
        "target": target_lang_code,
        "format": "text",
    }
    if source_lang_code and source_lang_code not in ("auto", ""):
        # Google accepts ISO codes like "en", "hi", "ur"
        body["source"] = source_lang_code.split("-")[0].lower()

    try:
        resp = requests.post(GOOGLE_TRANSLATE_URL, params=params, json=body, timeout=60)
    except requests.RequestException as e:
        raise UserFacingError("Translation service is temporarily unreachable. Please try again in a moment.") from e

    if resp.status_code == 403:
        raise UserFacingError(
            "Google Translate API key is invalid or Translation API is not enabled on the project. "
            "Enable Cloud Translation API and check the key."
        )
    if resp.status_code == 429:
        raise UserFacingError("Translation rate limit hit. Wait a minute and try again.")
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            detail = resp.text[:200]
        raise UserFacingError(f"Translation failed: {detail}")

    data = resp.json()
    try:
        translated = data["data"]["translations"][0]["translatedText"]
    except (KeyError, IndexError, TypeError) as e:
        raise UserFacingError("Unexpected response from translation service.") from e

    # Google HTML-escapes some characters even with format=text
    translated = (
        translated.replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    return translated.strip()


def _google_code_for_studio_lang(studio_lang: str) -> str:
    code = LANG_TO_GOOGLE.get(studio_lang)
    if not code:
        # Fallback: try first two letters of a voice id if somehow missing
        raise UserFacingError(f"Target language '{studio_lang}' is not supported for redub yet.")
    return code


def mux_audio_onto_video(video_bytes: bytes, video_filename: str, audio_bytes: bytes,
                         audio_ext: str = "mp3") -> bytes:
    """Replace the video's audio track with new audio. Video stream is stream-copied."""
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

        # -c:v copy keeps the original video; -c:a aac for broad player compatibility.
        # -shortest ends when the shorter stream ends (usually the new TTS track).
        # -map 0:v:0 -map 1:a:0 picks video from original, audio from new track.
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_path,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            out_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=180)
        if proc.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) < 100:
            err = (proc.stderr or b"").decode("utf-8", errors="replace")[:300]
            raise UserFacingError(f"Could not mux audio onto video. {err or 'ffmpeg failed.'}")

        with open(out_path, "rb") as f:
            return f.read()
    finally:
        for p in (video_path, audio_path, out_path):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass


def redub_video(
    video_bytes: bytes,
    filename: str,
    *,
    source_lang: str = "auto",
    target_studio_lang: str = "US English",
    voice_id: str = "en-US-JennyNeural",
    speed_pct: int = 100,
) -> dict:
    """
    Full redub pipeline. Returns dict with:
      video_b64, audio_b64, transcript, translated, filename, size_kb,
      source_lang_detected (optional), char_count
    """
    check_file_size(video_bytes, max_mb=MAX_VIDEO_MB)

    source_lang = (source_lang or "auto").strip()
    if source_lang not in TRANSCRIBE_LANGS:
        source_lang = "auto"

    # ---- 1. Extract audio ----
    audio_bytes = video_to_audio(video_bytes, filename, output_format="mp3", quality_kbps=192)

    # ---- 2. Transcribe ----
    tr = transcribe(audio_bytes, "extracted.mp3", source_lang)
    transcript = (tr.get("text") or "").strip()
    if not transcript:
        raise UserFacingError(
            "Could not detect speech in this video. Try a clearer audio track, "
            "or set the source language manually instead of Auto."
        )

    # Soft duration guard from transcription metadata if present
    duration = float(tr.get("duration_sec") or 0)
    if duration and duration > MAX_DURATION_SEC:
        raise UserFacingError(
            f"Video is about {int(duration // 60)} minutes — Phase 1 redub supports up to "
            f"{MAX_DURATION_SEC // 60} minutes. Trim the video first, or wait for longer limits."
        )

    # ---- 3. Translate ----
    target_code = _google_code_for_studio_lang(target_studio_lang)
    # Infer source code for Google from transcribe lang when not auto
    source_google = None
    if source_lang != "auto":
        source_google = source_lang.split("-")[0].lower()
        if source_google == "zh":
            source_google = "zh-CN"

    # Skip translation if source and target are the same language family
    same_lang = False
    if source_google and source_google == target_code:
        same_lang = True
    if same_lang:
        translated = transcript
    else:
        translated = translate_text(transcript, target_code, source_lang_code=source_google)

    if not translated:
        raise UserFacingError("Translation returned empty text.")

    # ---- 4. TTS with stock edge-tts voice ----
    speed_pct = max(50, min(200, int(speed_pct or 100)))
    rate_str = f"{speed_pct - 100:+d}%"
    tts_audio = tts_dispatch(translated, voice_id, rate=rate_str, ssml_mode=False, speed_pct=speed_pct)
    if not tts_audio:
        raise UserFacingError("Could not generate the dubbed voice track. Try another voice.")

    # ---- 5. Mux ----
    dubbed_video = mux_audio_onto_video(video_bytes, filename, tts_audio, audio_ext="mp3")

    ts = __import__("time").time()
    out_name = f"VoxCraft-Redub-{int(ts)}.mp4"
    audio_name = f"VoxCraft-Redub-Audio-{int(ts)}.mp3"

    return {
        "video_b64": base64.b64encode(dubbed_video).decode("ascii"),
        "audio_b64": base64.b64encode(tts_audio).decode("ascii"),
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
    }
