# VoxCraft Whisper Modal worker

GPU speech-to-text using **faster-whisper** (CTranslate2). Keeps the heavy
model off the VPS so lightweight hosts never OOM.

## Files

| Path | Role |
|------|------|
| `modal_workers/whisper/app.py` | Modal app + FastAPI endpoint |
| `modal_whisper.py` | VPS client (`transcribe_audio`) |
| `.github/workflows/deploy-modal-whisper-worker.yml` | Auto-deploy on push |

## Deploy

1. Ensure GitHub secrets `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` exist
   (same as Chatterbox / F5-TTS / ACE-Step).
2. Push to `main` under `modal_workers/whisper/**`, or run the workflow
   manually from Actions.
3. From the workflow log, copy the endpoint URL that ends with
   `...-whisperworker-transcribe.modal.run`.
4. On the VPS set:

```bash
export MODAL_WHISPER_ENDPOINT_URL="https://YOUR-WORKSPACE--voxcraft-whisper-worker-whisperworker-transcribe.modal.run"
```

(and add it to your process manager / `.env`).

## Wire into `audio_tools.transcribe`

Prefer Whisper when the Modal endpoint is configured; fall back to Google
Speech otherwise. Minimal change:

```python
# near top of audio_tools.py
try:
    import modal_whisper
except ImportError:
    modal_whisper = None

def transcribe(file_bytes: bytes, filename: str, lang_code: str, prefer_whisper: bool = True) -> dict:
    check_file_size(file_bytes)

    # --- GPU path (Modal faster-whisper) ---
    if prefer_whisper and modal_whisper is not None and modal_whisper.is_configured():
        # Map UI codes (en-US, hi-IN, ur-PK) → ISO-639-1
        lang = (lang_code or "").split("-")[0].lower() or None
        result = modal_whisper.transcribe_audio(
            file_bytes,
            language=lang,
            model_size="large-v3",  # or "turbo" for speed
            vad_filter=True,
        )
        if result.get("success"):
            text = (result.get("text") or "").strip()
            words = len(text.split()) if text else 0
            return {
                "text": text,
                "method": result.get("method") or "faster-whisper",
                "language": result.get("language") or lang_code,
                "word_count": words,
                "duration_sec": result.get("duration_sec") or 0.0,
                "segments_ok": 1,
                "segments_total": 1,
                "srt": result.get("srt") or "",
                "segments": result.get("segments") or [],
            }
        # Optional: log and fall through to Google
        # logger.warning("Whisper failed, falling back: %s", result.get("error"))

    # --- existing Google Speech path (unchanged) ---
    ...
```

You can also expose a UI checkbox “Use Whisper (GPU)” that passes
`prefer_whisper=True/False` into the API.

## Request / response shape

**POST** JSON body:

```json
{
  "audio_b64": "<base64>",
  "language": "hi",
  "task": "transcribe",
  "model_size": "large-v3",
  "word_timestamps": false,
  "vad_filter": true,
  "initial_prompt": null
}
```

**Response** (success):

```json
{
  "success": true,
  "text": "…",
  "language": "hi",
  "language_probability": 0.97,
  "duration_sec": 14.2,
  "segments": [{"start": 0.0, "end": 2.4, "text": "…"}],
  "srt": "1\n00:00:00,000 --> 00:00:02,400\n…",
  "method": "faster-whisper (large-v3)",
  "error": ""
}
```

## Notes

- Default GPU: **A10G**. Model is loaded once per container (`@modal.enter`).
- Cold start downloads weights on first ever deploy; later scale-from-zero
  only reloads from Modal’s cache (~15–40s depending on model).
- Supported languages include Urdu (`ur`) and Hindi (`hi`) — pass the
  ISO code; leave `language` null for auto-detect.
- `task: "translate"` forces English output regardless of source language.
- Max practical file size is still gated by the VPS `MAX_UPLOAD_MB` (10 MB
  in `audio_tools`); the worker itself can handle longer audio within the
  600s timeout.
