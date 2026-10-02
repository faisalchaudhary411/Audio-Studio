"""Local CPU transcription using whisper.cpp + Silero VAD.

Designed for the VoxCraft 1-vCPU / 2-GB VPS.  Uses a quantized multilingual
Whisper Base model, keeps one local inference job at a time, and parses the
VAD-aware SRT produced by whisper.cpp so timestamps stay on the original audio
timeline.  If this module is unavailable or a run fails, audio_tools.py falls
back to Google Speech.
"""

from __future__ import annotations

import fcntl
import os
import re
import subprocess
import tempfile
import time
from typing import Optional


WHISPER_DIR = os.path.expanduser(
    os.environ.get("VOXCRAFT_WHISPER_DIR", "~/whisper.cpp")
)
WHISPER_BIN = os.environ.get(
    "VOXCRAFT_WHISPER_BIN",
    os.path.join(WHISPER_DIR, "build", "bin", "whisper-cli"),
)
WHISPER_MODEL = os.environ.get(
    "VOXCRAFT_WHISPER_MODEL",
    os.path.join(WHISPER_DIR, "models", "ggml-base-q5_0.bin"),
)
VAD_MODEL = os.environ.get(
    "VOXCRAFT_WHISPER_VAD_MODEL",
    os.path.join(WHISPER_DIR, "models", "ggml-silero-v6.2.0.bin"),
)
LOCK_PATH = os.environ.get("VOXCRAFT_WHISPER_LOCK", "/tmp/voxcraft-whisper.lock")


def is_configured() -> bool:
    return (
        os.path.isfile(WHISPER_BIN)
        and os.access(WHISPER_BIN, os.X_OK)
        and os.path.isfile(WHISPER_MODEL)
        and os.access(WHISPER_MODEL, os.R_OK)
        and os.path.isfile(VAD_MODEL)
        and os.access(VAD_MODEL, os.R_OK)
    )


def _parse_timestamp(value: str) -> float:
    """Convert SRT/Whisper timestamp text to seconds."""
    value = str(value or "").strip().replace(",", ".")
    if not value:
        return 0.0
    try:
        parts = value.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(value)
    except Exception:
        return 0.0


_SRT_RE = re.compile(
    r"(?ms)^\s*(\d+)\s*\n"
    r"\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+"
    r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\n"
    r"(.*?)(?=\n\s*\n|\Z)"
)


def _segments_from_srt(srt: str) -> list[dict]:
    result = []
    for match in _SRT_RE.finditer(srt or ""):
        start = _parse_timestamp(match.group(2))
        end = _parse_timestamp(match.group(3))
        text = re.sub(r"\s+", " ", match.group(4).strip())
        if not text or end <= start:
            continue
        result.append({
            "id": len(result),
            "start": round(start, 3),
            "end": round(end, 3),
            "text": text,
        })
    return result


def _fmt_srt_time(seconds: float) -> str:
    ms_total = max(0, int(round(float(seconds) * 1000)))
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _segments_to_srt(segments: list[dict]) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(
            f"{_fmt_srt_time(seg['start'])} --> {_fmt_srt_time(seg['end'])}"
        )
        lines.append(seg["text"].strip())
        lines.append("")
    return "\n".join(lines)


def transcribe(
    audio_bytes: bytes,
    language: Optional[str] = None,
    timeout_sec: int = 360,
    *,
    model_path: Optional[str] = None,
    prompt: Optional[str] = None,
    wait_sec: float = 0.0,
) -> dict:
    """Run whisper.cpp locally and return text, real segments and SRT."""
    if not is_configured():
        return {"success": False, "error": "Local whisper.cpp is not installed/configured."}
    use_model = WHISPER_MODEL
    if model_path and os.path.isfile(model_path) and os.access(model_path, os.R_OK):
        use_model = model_path
    if not audio_bytes:
        return {"success": False, "error": "Empty audio payload."}

    lock_file = None
    acquired = False
    tmpdir = None

    try:
        # One local inference at a time: this VPS has only one CPU core.
        lock_file = open(LOCK_PATH, "a+")
        # wait_sec > 0: queue behind the running job instead of failing at once
        # (used by Video Redub so a second request waits rather than using Google).
        deadline = time.monotonic() + max(0.0, float(wait_sec or 0.0))
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    lock_file.close()
                    lock_file = None
                    return {"success": False, "error": "Local transcription is busy."}
                time.sleep(1.0)

        tmpdir = tempfile.mkdtemp(prefix="voxcraft-whisper-")
        input_path = os.path.join(tmpdir, "input.wav")
        out_prefix = os.path.join(tmpdir, "transcription")

        with open(input_path, "wb") as f:
            f.write(audio_bytes)

        cmd = [
            WHISPER_BIN,
            "-m", use_model,
            "-vm", VAD_MODEL,
            "--vad",
            "-t", "1",
            "-p", "1",
            "-osrt",
            "-otxt",
            "-of", out_prefix,
            "-np",
            # No carry-over context between windows: stops repetition loops
            "-mc", "0",
        ]
        if language and language.lower() not in {"auto", "none", "detect"}:
            cmd.extend(["-l", language.lower().split("-")[0]])
        # The input audio MUST be passed, otherwise whisper-cli prints its usage
        # text and exits with code 2 ("speech recognition ..." help banner).
        if prompt:
            # Initial prompt biases script + vocabulary (e.g. Hinglish tech terms)
            cmd.extend(["--prompt", prompt])
        cmd.extend(["-f", input_path])

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(30, int(timeout_sec)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Local whisper.cpp timed out."}
        except Exception as exc:
            return {"success": False, "error": f"Local whisper.cpp failed to start: {exc}"}

        srt_path = out_prefix + ".srt"
        txt_path = out_prefix + ".txt"
        if proc.returncode != 0:
            tail = (proc.stdout or "").strip()[-500:]
            return {"success": False, "error": f"whisper.cpp exited with code {proc.returncode}: {tail}"}

        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                srt = f.read().strip()
        except Exception as exc:
            return {"success": False, "error": f"Could not read whisper.cpp SRT: {exc}"}

        segments = _segments_from_srt(srt)
        if not segments:
            return {"success": False, "error": "Whisper produced no speech segments."}

        # Prefer the plain transcript generated by whisper.cpp, while falling
        # back to the segment text if the .txt file is unavailable.
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
        except Exception:
            text = " ".join(s["text"] for s in segments).strip()

        if not text:
            text = " ".join(s["text"] for s in segments).strip()

        return {
            "success": True,
            "text": text,
            "segments": segments,
            "srt": srt or _segments_to_srt(segments),
            "method": "whisper.cpp Base Q5 + Silero VAD",
            "language": language or "auto",
            "engine": "whisper.cpp",
        }

    finally:
        if tmpdir:
            try:
                for name in os.listdir(tmpdir):
                    try:
                        os.unlink(os.path.join(tmpdir, name))
                    except OSError:
                        pass
                os.rmdir(tmpdir)
            except OSError:
                pass
        if lock_file:
            try:
                if acquired:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file.close()
