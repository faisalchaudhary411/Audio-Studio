# VoxCraft updates — AdSense readiness pack
Generated: 2026-09-04

## What this pack contains

### 1. Adsterra reactivation (non-intrusive)
- `templates/base.html` — mobile sticky footer for free users
- `templates/landing.html` — banner after proof-band
- `templates/blog_list.html` — banner after filters
- `templates/blog_detail.html` — banner after article body
- `templates/pricing.html` — banner after plan cards
- `templates/partials/ads_banner.html` + `ads_global.html` (unchanged, included for completeness)

Popunder + interstitial remain OFF (env-gated) for AdSense review safety.

### 2. Must-have pages (E-E-A-T)
- `templates/about.html` — strengthened: ownership, location focus, editorial standards, contact

Privacy, Terms, Contact were already solid and are not modified.

### 3. Blog admin upgrade (screenshots + long-form)
- `templates/admin/blog.html` — image upload, larger editor, Markdown cheat sheet for tables/screenshots
- `app.py` — image upload handler (`static/blog/`), appends Markdown into body on save
- `static/css/style.css` — blog screenshot + comparison table styles
- `static/blog/.gitkeep` — ensures the upload folder exists in git

## How to apply

From your repo root:

```bash
# Option A — copy over existing files
cp -R path/to/voxcraft-all-updates/templates/* templates/
cp path/to/voxcraft-all-updates/app.py .
cp path/to/voxcraft-all-updates/static/css/style.css static/css/
mkdir -p static/blog && touch static/blog/.gitkeep

# Option B — if you prefer git
# merge the files carefully, especially app.py
```

Then restart / redeploy the app.

## After deploy

1. Visit `/admin/blog` as admin — confirm image upload works.
2. Spot-check landing, blog, pricing, studio as a free user (ads should show).
3. Confirm Pro users see no ads.
4. Delete thin 1–2 min posts, then publish long guides with screenshots.

## Env vars (unchanged, for reference)

- `ENABLE_POPUNDER=1` — turn popunder back on (keep OFF until AdSense approved)
- `ENABLE_INTERSTITIAL=1` — turn interstitial back on (keep OFF for now)
- `ADSENSE_PUBLISHER_ID` — already wired for Auto Ads when set
