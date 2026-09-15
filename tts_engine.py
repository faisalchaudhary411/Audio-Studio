"""
tts_engine.py — ported from the Streamlit VoxCraft app almost line-for-line.

Kept identical:
- generate_audio() / generate_audio_markup() retry logic (3 attempts, backoff)
- _make_silence() real decodable silent MP3 for [pause] tags
- parse_markup_segments() markup tag parser (pause/strong/em/slow/fast/high/low/whisper)
- tts_dispatch() central routing function

Fallback chain (stock neural voices — Studio, redub, previews):
  1. edge-tts (free)
  2. Azure Speech REST (if AZURE_SPEECH_KEY + AZURE_SPEECH_REGION set)
     — same voice short-names (e.g. pa-IN-OjasNeural)
  3. gTTS (generic per-language, last resort)

NOT ported yet (marked TODO): ElevenLabs cloned-voice routing (EL:: prefix).
"""

import asyncio
import io
import os
import re
import xml.sax.saxutils

import edge_tts
import lameenc

try:
    import requests as _requests
except ImportError:
    _requests = None

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# Optional paid neural fallback — same Microsoft voice IDs as Edge, full catalogue.
AZURE_SPEECH_KEY = (os.environ.get("AZURE_SPEECH_KEY") or "").strip()
AZURE_SPEECH_REGION = (os.environ.get("AZURE_SPEECH_REGION") or "").strip()

_SILENCE_SAMPLE_RATE = 24000


def _make_silence(duration_ms: int) -> bytes:
    """Generate a real, decodable silent MP3 clip for [pause] tags."""
    n_samples = max(1, int(_SILENCE_SAMPLE_RATE * duration_ms / 1000))
    pcm = b"\x00\x00" * n_samples  # 16-bit silent PCM, mono
    enc = lameenc.Encoder()
    enc.set_bit_rate(48)
    enc.set_in_sample_rate(_SILENCE_SAMPLE_RATE)
    enc.set_channels(1)
    enc.set_quality(2)
    data = enc.encode(pcm)
    data += enc.flush()
    return data


def apply_pronunciation_dict(text: str, entries: list) -> str:
    """Global find/say substitution applied to Studio TTS input before it
    reaches edge-tts — e.g. 'Nginx' -> 'Engine-X' so the engine says
    something closer to correct instead of sounding it out literally.

    Deliberately plain text substitution, not SSML <phoneme> tags: the
    edge-tts library wraps Microsoft Edge's free read-aloud feature rather
    than the full Azure Cognitive Services SSML surface, and doesn't
    expose phoneme-level pronunciation control. Respelling the word in the
    input text is the reliable lever available with this engine — and it
    has the added benefit of working identically through the gTTS
    fallback path too, since that's plain text as well.

    Each entry: {"find": "...", "say": "...", "match_case": bool}.
    - Word-boundary matched (\\b), so "Go" doesn't also rewrite "Google".
    - Case-insensitive by default; set match_case=true for entries where
      capitalization matters (rare, but e.g. distinguishing an acronym
      from a common word that happens to share letters).
    - Matches are found longest-find-string-first, so a more specific
      multi-word entry doesn't get pre-empted by a shorter one contained
      inside it.
    """
    if not entries or not text:
        return text

    ordered = sorted(entries, key=lambda e: len(e.get("find", "")), reverse=True)
    for entry in ordered:
        find = (entry.get("find") or "").strip()
        say = entry.get("say", "")
        if not find:
            continue
        flags = 0 if entry.get("match_case") else re.IGNORECASE
        try:
            pattern = re.compile(r"\b" + re.escape(find) + r"\b", flags)
        except re.error:
            continue  # skip a malformed entry rather than failing the whole generation
        text = pattern.sub(lambda m, _say=say: _say, text)
    return text


_MARKUP_RE = re.compile(
    r"\[pause:(\d+(?:\.\d+)?(?:ms|s))\]"
    r"|\[strong\](.*?)\[/strong\]"
    r"|\[em\](.*?)\[/em\]"
    r"|\[slow\](.*?)\[/slow\]"
    r"|\[fast\](.*?)\[/fast\]"
    r"|\[high\](.*?)\[/high\]"
    r"|\[low\](.*?)\[/low\]"
    r"|\[whisper\](.*?)\[/whisper\]"
    r"|\[excited\](.*?)\[/excited\]"
    r"|\[serious\](.*?)\[/serious\]"
    r"|\[calm\](.*?)\[/calm\]"
    r"|\[cheerful\](.*?)\[/cheerful\]"
    r"|\[sad\](.*?)\[/sad\]",
    re.DOTALL,
)


def parse_markup_segments(text: str, base_rate: str) -> list:
    segments = []

    def add_text(t, rate=None, volume="+0%", pitch="+0Hz"):
        t = t.strip()
        if t:
            segments.append({"type": "text", "text": t, "rate": rate or base_rate, "volume": volume, "pitch": pitch})

    last = 0
    for m in _MARKUP_RE.finditer(text):
        if m.start() > last:
            add_text(text[last:m.start()])
        g = m.groups()
        if g[0]:
            raw = g[0]
            ms = int(float(raw[:-2])) if raw.endswith("ms") else int(float(raw[:-1]) * 1000)
            segments.append({"type": "pause", "ms": ms})
        elif g[1] is not None: add_text(g[1], volume="+30%")
        elif g[2] is not None: add_text(g[2], volume="+15%")
        elif g[3] is not None: add_text(g[3], rate="-30%")
        elif g[4] is not None: add_text(g[4], rate="+50%")
        elif g[5] is not None: add_text(g[5], pitch="+10Hz")
        elif g[6] is not None: add_text(g[6], pitch="-10Hz")
        elif g[7] is not None: add_text(g[7], volume="-50%", pitch="-5Hz")
        # Named "expression" presets — combinations of the same rate/pitch/
        # volume levers above, just bundled under a more intuitive name.
        # NOT true emotional synthesis (edge-tts doesn't expose Azure's
        # mstts:express-as styles) — these approximate a feeling through
        # pacing, pitch and loudness only. Good enough to noticeably
        # change delivery; won't sound like a different acting choice.
        elif g[8] is not None: add_text(g[8], rate="+20%", pitch="+8Hz", volume="+20%")   # excited
        elif g[9] is not None: add_text(g[9], rate="-15%", pitch="-5Hz")                   # serious
        elif g[10] is not None: add_text(g[10], rate="-10%", volume="-10%")                # calm
        elif g[11] is not None: add_text(g[11], rate="+10%", pitch="+12Hz")                # cheerful
        elif g[12] is not None: add_text(g[12], rate="-20%", pitch="-8Hz", volume="-15%")  # sad
        last = m.end()
    if last < len(text):
        add_text(text[last:])
    return segments


async def generate_audio_markup(text: str, voice: str, rate: str = "+0%") -> bytes:
    segments = parse_markup_segments(text, rate)
    parts = []
    for seg in segments:
        if seg["type"] == "pause":
            parts.append(_make_silence(seg["ms"]))
        else:
            last_err = None
            for attempt in range(3):
                try:
                    com = edge_tts.Communicate(seg["text"], voice, rate=seg["rate"], volume=seg["volume"], pitch=seg["pitch"])
                    audio = b""
                    async for chunk in com.stream():
                        if chunk["type"] == "audio":
                            audio += chunk["data"]
                    if audio:
                        parts.append(audio)
                        break
                    last_err = Exception("No audio returned.")
                except Exception as e:
                    last_err = e
                    if attempt < 2:
                        await asyncio.sleep(1.5 * (attempt + 1))
            else:
                raise last_err
    if not parts:
        raise Exception("No audio generated from markup text.")
    return b"".join(parts)


async def generate_audio(text: str, voice: str, rate: str = "+0%") -> bytes:
    last_err = None
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            if audio_data:
                return audio_data
            last_err = Exception("No audio returned by the TTS service.")
        except Exception as e:
            last_err = e
            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
    raise last_err


# Map full Edge/Azure voice short-names (or their locale prefix) to a gTTS
# language code. gTTS only has one generic voice per language — no gender —
# so this is a last-resort path when the primary neural engine rejects a
# voice ID (common for newer Indian locales like pa-IN that exist on Azure
# Speech but are not always exposed on the free Edge Read Aloud endpoint).
_GTTS_LANG_MAP = {
    "en": "en", "en-US": "en", "en-GB": "en", "en-AU": "en", "en-IN": "en",
    "hi": "hi", "hi-IN": "hi",
    "ur": "ur", "ur-PK": "ur", "ur-IN": "ur",
    "pa": "pa", "pa-IN": "pa",          # Punjabi (Gurmukhi) — single generic voice
    "bn": "bn", "bn-IN": "bn", "bn-BD": "bn",
    "ta": "ta", "ta-IN": "ta",
    "te": "te", "te-IN": "te",
    "ar": "ar", "ar-SA": "ar", "ar-EG": "ar",
    "es": "es", "es-ES": "es", "es-MX": "es",
    "fr": "fr", "fr-FR": "fr", "fr-CA": "fr",
    "de": "de", "de-DE": "de",
    "it": "it", "it-IT": "it",
    "pt": "pt", "pt-BR": "pt", "pt-PT": "pt",
    "ru": "ru", "ru-RU": "ru",
    "ja": "ja", "ja-JP": "ja",
    "ko": "ko", "ko-KR": "ko",
    "zh": "zh-CN", "zh-CN": "zh-CN", "zh-TW": "zh-TW", "zh-HK": "zh-TW",
    "tr": "tr", "tr-TR": "tr",
    "pl": "pl", "pl-PL": "pl",
    "nl": "nl", "nl-NL": "nl",
    "sv": "sv", "sv-SE": "sv",
    "id": "id", "id-ID": "id",
    "ms": "ms", "ms-MY": "ms",
    "th": "th", "th-TH": "th",
    "vi": "vi", "vi-VN": "vi",
    "cs": "cs", "cs-CZ": "cs",
    "da": "da", "da-DK": "da",
    "fi": "fi", "fi-FI": "fi",
    "el": "el", "el-GR": "el",
    "he": "iw", "he-IL": "iw",          # gTTS still uses legacy 'iw' for Hebrew
    "hu": "hu", "hu-HU": "hu",
    "nb": "no", "nb-NO": "no",
    "ro": "ro", "ro-RO": "ro",
    "sk": "sk", "sk-SK": "sk",
    "uk": "uk", "uk-UA": "uk",
    "fil": "tl", "fil-PH": "tl",        # Filipino → Tagalog code in gTTS
    "ca": "ca", "ca-ES": "ca",
    "hr": "hr", "hr-HR": "hr",
    "bg": "bg", "bg-BG": "bg",
}


def _voice_to_gtts_lang(voice: str) -> str:
    """Resolve an Edge-style voice ID to the best gTTS language code."""
    if not voice:
        return "en"
    # Full short-name e.g. pa-IN-OjasNeural → try locale then language
    parts = voice.replace("Neural", "").replace("Multilingual", "").strip("-").split("-")
    # Try "pa-IN", then "pa"
    if len(parts) >= 2:
        locale = f"{parts[0]}-{parts[1]}"
        if locale in _GTTS_LANG_MAP:
            return _GTTS_LANG_MAP[locale]
    lang = parts[0] if parts else "en"
    return _GTTS_LANG_MAP.get(lang, lang if len(lang) == 2 else "en")


def _azure_configured() -> bool:
    return bool(AZURE_SPEECH_KEY and AZURE_SPEECH_REGION and _requests is not None)


def _rate_to_azure_prosody(rate: str) -> str:
    """Map edge-style rate ('+10%', '-5%', '+0%') to Azure prosody rate attribute."""
    r = (rate or "+0%").strip()
    if not r:
        return "0%"
    if r[0] not in "+-":
        r = "+" + r
    return r


def _azure_tts(text: str, voice: str, rate: str = "+0%") -> bytes:
    """Synthesize via Azure Cognitive Services Speech REST API.

    Uses the same voice short-name as edge-tts (e.g. en-US-JennyNeural,
    pa-IN-OjasNeural). Requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.
    Returns MP3 bytes (audio-24khz-48kbitrate-mono-mp3).
    """
    if not _azure_configured():
        raise Exception("Azure Speech is not configured (AZURE_SPEECH_KEY / AZURE_SPEECH_REGION).")
    if not (text or "").strip():
        raise Exception("Empty text for Azure TTS.")
    voice = (voice or "").strip()
    if not voice:
        raise Exception("No voice ID for Azure TTS.")

    # Locale from voice short-name: pa-IN-OjasNeural → pa-IN
    parts = voice.split("-")
    locale = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else "en-US"
    safe_text = xml.sax.saxutils.escape(text)
    prosody_rate = _rate_to_azure_prosody(rate)
    ssml = (
        f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{locale}'>"
        f"<voice name='{xml.sax.saxutils.escape(voice)}'>"
        f"<prosody rate='{prosody_rate}'>{safe_text}</prosody>"
        f"</voice></speak>"
    )
    url = f"https://{AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "VoxCraft",
    }
    resp = _requests.post(url, data=ssml.encode("utf-8"), headers=headers, timeout=60)
    if resp.status_code != 200:
        detail = (resp.text or "")[:180]
        raise Exception(f"Azure Speech HTTP {resp.status_code}: {detail}")
    audio = resp.content
    if not audio or len(audio) < 64:
        raise Exception("Azure Speech returned empty audio.")
    return audio


def _gtts_fallback(text: str, voice: str, speed_pct: int = 100) -> bytes:
    """Last-resort fallback using gTTS when neural engines fail.

    gTTS has only one generic voice per language (no real male/female choice).
    """
    if not GTTS_AVAILABLE:
        raise Exception("gTTS is not installed / available as a fallback engine.")
    lang = _voice_to_gtts_lang(voice)
    buf = io.BytesIO()
    gTTS(text=text, lang=lang, slow=(speed_pct < 80)).write_to_fp(buf)
    return buf.getvalue()


def _inject_sentence_pauses(text: str, pause_ms: int = 280) -> str:
    """Insert lightweight [pause] tags between sentences for more natural pacing.

    Only used when markup mode is off and auto_pause is enabled.
    """
    import re
    if not text or "[pause:" in text:
        return text
    parts = re.split(r"(?<=[.!?。؟۔।॥])\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        return text
    tag = f"[pause:{pause_ms}ms]"
    return f" {tag} ".join(parts)


def tts_dispatch(text: str, voice_id: str, rate: str = "+0%", ssml_mode: bool = False,
                 speed_pct: int = 100, auto_pause: bool = False, _meta: dict | None = None) -> bytes:
    """Central TTS routing for stock voices (Studio, redub, previews).

    Chain:
      1. edge-tts (free)
      2. Azure Speech (same voice ID) if AZURE_SPEECH_KEY + REGION are set
      3. gTTS last resort (generic language voice only)

    _meta receives engine name: edge-tts | azure_fallback | gtts_fallback
    so callers can show an honest notice only when quality may differ.
    """
    def _mark(engine: str, reason: str = ""):
        if _meta is not None:
            _meta["engine"] = engine
            if reason:
                _meta["fallback_reason"] = reason[:200]

    edge_err: Exception | None = None
    try:
        if ssml_mode:
            result = asyncio.run(generate_audio_markup(text, voice_id, rate=rate))
            _mark("edge-tts")
            return result
        if auto_pause:
            paused = _inject_sentence_pauses(text)
            if paused != text:
                result = asyncio.run(generate_audio_markup(paused, voice_id, rate=rate))
                _mark("edge-tts")
                return result
        result = asyncio.run(generate_audio(text, voice_id, rate=rate))
        _mark("edge-tts")
        return result
    except Exception as e:
        edge_err = e

    # ── Azure neural fallback (same voice short-name) ─────────────────
    if _azure_configured():
        try:
            # Markup path is flattened to plain text for Azure SSML
            plain = text
            if ssml_mode or auto_pause:
                plain = re.sub(r"\[(?:pause|strong|em|slow|fast|high|low|whisper)[^\]]*\]", " ", text)
                plain = re.sub(r"\s+", " ", plain).strip() or text
            result = _azure_tts(plain, voice_id, rate=rate)
            _mark("azure_fallback", str(edge_err) if edge_err else "")
            return result
        except Exception as azure_err:
            edge_err = azure_err  # surface last error if gTTS also fails

    # ── gTTS last resort ──────────────────────────────────────────────
    try:
        result = _gtts_fallback(text, voice_id, speed_pct=speed_pct)
        _mark("gtts_fallback", str(edge_err) if edge_err else "")
        return result
    except Exception:
        if edge_err:
            raise edge_err
        raise
