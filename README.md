# VoxCraft — Flask migration

## Status: TTS tool ported for real. Everything else is NOT ported yet.

This pass replaced the stub `/api/generate` with an actual port of your Streamlit
TTS engine — edge-tts + gTTS fallback, retry logic, markup/SSML mode, single +
batch generation with ZIP export, voice preview, free/Pro voice-list gating,
daily usage limits. It's a faithful port of the `tts_dispatch` / `generate_audio`
/ `generate_audio_markup` / `parse_markup_segments` / `_make_silence` functions
from your `app__1_.py`.

**Still NOT ported** (your Streamlit app has 9 tools total — this is TTS only):
Transcribe, Audio Converter, Merge, Cutter, Music tool, Denoise, Voice Changer,
Video-to-Audio extractor, admin panel, Freemius/Paddle payment callbacks,
license-key system, IP-based usage tracking, ad system (6 surfaces), blog.

- `app.py` — routes: `/`, `/studio`, `/pricing`, `/api/tts/preview`, `/api/tts/generate`, `/api/tts/batch`
- `tts_engine.py` — ported TTS engine (edge-tts, gTTS fallback, markup parser)
- `voices.py` — full + free voice catalogues (ported from `app__1_.py`)
- `templates/studio.html` + `static/js/studio.js` — real voice picker, SSML toggle, single/batch UI
- `static/css/style.css` — design system (ink-teal + brass/jade palette)
- `Procfile` + `requirements.txt` — includes edge-tts, gTTS, lameenc

## What YOU need to wire in (marked with `TODO` in app.py / tts_engine.py)
1. **Real Pro / license check** — `is_pro()` is a session-cookie stub. Your original
   app used IP-based usage tracking synced through your GitHub backend — this
   Flask version uses Flask session cookies instead, which is NOT equivalent
   (resets per-browser, not per-IP/device). Wire in your real license-key check
   before relying on the free-tier limits.
2. **ElevenLabs cloned voices** (`EL::` prefix) — stripped out this pass. Re-add
   `el_generate_audio()` and the routing branch in `tts_dispatch()` if needed.
3. **Google-engine voices** (`GT::` prefix, "More Languages" category) — stripped
   out this pass; those route through gTTS directly, not edge-tts.
4. **The other 8 tools + admin + payments + ads + blog** — not started.

## Testing locally / on Replit
```
pip install -r requirements.txt
python app.py
```
Visit `/`, `/studio`, `/pricing`, `/admin`.

## Deploying on Render (not Vercel — see why below)
1. Push this repo to GitHub.
2. In Render: New → Blueprint → point at the repo (it'll read `render.yaml` automatically),
   or New → Web Service manually with:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT`
3. Free tier works fine for this app (landing + TTS via edge-tts, no heavy ML deps).
   Free services spin down after 15 min idle and take ~30-60s to wake back up on
   the next request — acceptable for a solo project, upgrade to Starter ($7/mo)
   if the cold start becomes annoying.

### Why not Vercel for this app
Vercel is serverless — no persistent process, ephemeral filesystem, and a strict
function timeout (10s free / 60s Pro by default). Fine for simple stateless APIs,
bad fit for anything with real generation time or that needs to hold state
between requests. Render (or Railway) is the better fit for a Flask app like this.

## Voice cloning — deliberately NOT deployed yet
`clone_engine.py` + the `/api/clone/*` routes exist in the code but need
`requirements-clone.txt` installed (Chatterbox-Turbo + CPU torch) on an instance
with real RAM — no free tier anywhere (Render, Railway, Vercel) has enough RAM
for this. The one free hosted alternative (Hugging Face's public Chatterbox
Space) is currently paused, which is exactly the reliability risk with
depending on someone else's free Space for a paid feature.
**Recommendation: hold off on shipping cloning until you're ready to pay for
~2GB RAM somewhere (~$25/mo), rather than build it against something fragile.**
The main app works fully without it — cloning is additive.

## Design notes
The whole visual identity is built around the product's actual mechanism — text → voice → audio —
rather than generic dashboard styling. The hero waveform is live CSS/JS, not a static image.
Palette: ink-teal `#101820` bg, brass `#E8A93C` primary accent, jade `#4FA69C` secondary.
