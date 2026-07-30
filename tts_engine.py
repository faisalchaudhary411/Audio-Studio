"""
tts_engine.py — ported from the Streamlit VoxCraft app almost line-for-line.

Kept identical:
- generate_audio() / generate_audio_markup() retry logic (3 attempts, backoff)
- _make_silence() real decodable silent MP3 for [pause] tags
- parse_markup_segments() markup tag parser (pause/strong/em/slow/fast/high/low/whisper)
- _gtts_fallback() as the fallback engine when edge-tts fails
- tts_dispatch() central routing function

NOT ported yet (marked TODO): ElevenLabs cloned-voice routing (EL:: prefix).
Add el_generate_audio() back in and re-enable the branch in tts_dispatch()
if you want cloned voices in this version.
"""

import asyncio
import io
import re

import edge_tts
import lameenc

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

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


_MARKUP_RE = re.compile(
    r"\[pause:(\d+(?:\.\d+)?(?:ms|s))\]"
    r"|\[strong\](.*?)\[/strong\]"
    r"|\[em\](.*?)\[/em\]"
    r"|\[slow\](.*?)\[/slow\]"
    r"|\[fast\](.*?)\[/fast\]"
    r"|\[high\](.*?)\[/high\]"
    r"|\[low\](.*?)\[/low\]"
    r"|\[whisper\](.*?)\[/whisper\]",
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


def _gtts_fallback(text: str, voice: str, speed_pct: int = 100) -> bytes:
    """Fallback engine using gTTS when edge-tts fails. Maps edge-tts voice
    codes (e.g. 'en-US-JennyNeural') to a gTTS language code (e.g. 'en')."""
    if not GTTS_AVAILABLE:
        raise Exception("gTTS is not installed / available as a fallback engine.")
    lang = voice.split("-")[0] if "-" in voice else "en"
    buf = io.BytesIO()
    gTTS(text=text, lang=lang, slow=(speed_pct < 80)).write_to_fp(buf)
    return buf.getvalue()


def tts_dispatch(text: str, voice_id: str, rate: str = "+0%", ssml_mode: bool = False, speed_pct: int = 100) -> bytes:
    """Central TTS routing function.

    - voice_id starting with 'GT::' -> not handled here yet, route to gTTS directly (see app.py)
    - ssml_mode True                -> markup-aware generator
    - otherwise                     -> plain edge-tts, with gTTS as fallback if edge-tts fails
    """
    try:
        if ssml_mode:
            return asyncio.run(generate_audio_markup(text, voice_id, rate=rate))
        return asyncio.run(generate_audio(text, voice_id, rate=rate))
    except Exception as e:
        try:
            return _gtts_fallback(text, voice_id, speed_pct=speed_pct)
        except Exception:
            raise e
