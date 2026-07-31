# VoxCraft — Flask migration

## Status: TTS + 4 audio tools + full management layer ported. 4 audio tools remain.

### This round: licensing, admin, ads, blog, legal pages
Ported from your Streamlit backend and functionally tested end-to-end in this
environment (not just route wiring — actual license activation/device-binding,
IP usage limits, request approval → key email, and blog markdown rendering
were all verified with real test data before handing off):

- **Licensing** (`licensing.py`) — your internal key system: generate, activate
  (with same-device re-activation via IP+fingerprint matching), revoke,
  unrevoke, delete, renew. Plus Freemius verification. **Paddle was NOT
  ported** — per your own project history, Freemius replaced Paddle after
  Paddle rejected the app, so Paddle was already dead code in the original.
- **Usage tracking** (`usage_tracking.py`) — real IP-based (not session-cookie)
  free-tier limits, hashed IP + browser fingerprint, synced to GitHub.
- **Manual pro requests** (`pro_requests.py`) — EasyPaisa/JazzCash/HBL bank
  transfer flow: customer submits proof at `/upgrade`, you approve in
  `/admin/requests`, they get an emailed license key automatically.
- **Admin panel** (`/admin/*`) — dashboard, pricing/limits editor, license key
  manager, pro-requests queue, blog manager. **Password-gated — the original
  had NO auth on `/admin` at all, which I added here** (`ADMIN_PASSWORD`).
- **Ads** — your real Adsterra codes (sticky footer, in-page push, banner,
  interstitial), ported as-is, gated to free users only.
- **Blog** — public `/blog` + `/blog/<id>`, Markdown body rendering, full CRUD
  in the admin panel, persisted to GitHub same as your other config data.
- **Privacy / Terms / Contact** — new pages (didn't exist in the original).
  These are starting templates, not legal advice — have them reviewed,
  especially before handling Pakistani payment data.

### One thing worth fixing (found while testing, ported faithfully rather than
silently changed): your original `check_vox_license()` has the revoked-key
check placed after the expiry check, which already returns early for revoked
keys — so revoked keys report "Subscription expired" instead of "revoked".
Cosmetic only, but flagging since you may want the message accurate.

## REQUIRED environment variables (set these in Render before deploying)
| Variable | Purpose | What breaks without it |
|---|---|---|
| `GITHUB_TOKEN` | repo-scope PAT for `faisalchaudhary411/faisalchaudhary411.github.io` | Nothing persists — limits/keys/requests/blog all silently no-op |
| `ADMIN_PASSWORD` | gates `/admin` | Admin panel redirects to login forever (no password = can't log in) |
| `SECRET_KEY` | Flask session signing | Sessions won't persist reliably across restarts |
| `RESEND_API_KEY` + `ADMIN_EMAIL` | pro-request notification emails | Requests still queue in admin, just no email alert |
| `FREEMIUS_API_TOKEN` + `FREEMIUS_PRODUCT_ID` | Freemius license verification | Only needed if you wire up Freemius checkout; manual bank-transfer flow works without it |

## Newly ported earlier: Transcribe, Convert, Merge, Cutter
Live under `/tools` — pydub + ffmpeg (preinstalled on Render). See git history
of this README for details.

**Still NOT ported**: Music tool, Denoise, Voice Changer, Video-to-Audio
extractor.

## Voice cloning — deliberately NOT deployed yet
See earlier note: no free tier has enough RAM for Chatterbox, and the free
hosted alternative (HF's public Chatterbox Space) is currently paused. Hold
off until you're ready to pay for ~2GB RAM somewhere.

## Deploying on Render
1. Push to GitHub, including all the env vars above set in Render's dashboard.
2. New → Blueprint → point at the repo (reads `render.yaml` automatically).
3. Free tier is fine for everything in this app — no heavy ML deps.

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
