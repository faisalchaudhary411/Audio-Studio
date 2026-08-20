# VoxCraft — Phase 3 content: real blog posts + related fixes

2 files, same repo structure — overwrite app.py, and add seed_blog_posts.py
as a NEW file at your repo root (same level as app.py).

## Files
- app.py (MODIFIED — 3 separate fixes, see below)
- seed_blog_posts.py (NEW — one-time content seeding script)

## What this does

**1. Publishes 10 real blog posts** covering the full product surface:
Urdu TTS narration, TTS vs human voiceover, transcription, noise removal,
audio format comparison (MP3/WAV/FLAC), voice cloning ethics, merge/trim,
AI music licensing, voice changer use cases, and video-to-audio extraction.
Each is a genuine 400-500 word guide with real structure (headers, lists,
practical steps) — not filler. Every post has a `related_tool` field that
now correctly links to its matching dedicated tool page.

**2. Fixed BLOG_TOOL_LINKS (real bug, found while wiring this up)**
Every non-TTS entry in this mapping still pointed at the generic `/tools`
hub, left over from before the Phase 2 restructure gave each tool its own
dedicated page. A blog post about denoising was linking to the whole tools
directory instead of straight to `/tools/remove-background-noise`. Fixed
every entry to point at its specific page, and added a `voice cloning`
entry (there wasn't one before) pointing at `/voice-cloning`.

**3. Fixed a markdown rendering bug (real bug, would've broken silently)**
`md_lib.markdown()` on the blog detail page didn't have the `tables`
extension enabled — any post using a markdown table (like the MP3/WAV/FLAC
comparison table in one of the new posts) would render as broken raw
pipe-text instead of an actual table. Added `extensions=["tables",
"fenced_code"]` so tables render correctly and code blocks are supported
for any future technical posts.

## How to run seed_blog_posts.py

This writes directly through your existing `persistence.py` layer — same
functions the admin panel uses — so it needs to run in the same
environment as the live app (same `DB_PATH`, same working directory).

On the VPS, from the repo root:
```
python3 seed_blog_posts.py
```

It's safe to run more than once — it checks post titles against what's
already in the DB and skips duplicates, so re-running after you've added
more posts manually won't create copies.

After running, check `/admin/blog` to confirm all 10 appear, then spot
check a couple on the live site.

## Testing performed
- Ran seed_blog_posts.py against a real, isolated SQLite database (not a
  mock) — confirmed all 10 posts insert correctly, and confirmed
  re-running it correctly skips all 10 as duplicates (idempotency check).
- Rendered blog_list.html and blog_detail.html for every single post
  through a real Flask app with real Jinja templates.
- Ran every post's body through the actual markdown library, exactly as
  app.py does, including the tables extension fix.
- Verified every post's related_tool value resolves through the fixed
  BLOG_TOOL_LINKS to a real url_for() URL, and confirmed that URL actually
  appears in the rendered detail page HTML.
- Verified the tool_page keyword-matching logic (built in Phase 2) picks
  up the new posts as "related articles" on the correct tool pages.
