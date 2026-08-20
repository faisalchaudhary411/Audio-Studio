# VoxCraft — Phase 1–2.5 combined patch

This zip has the SAME folder structure as your repo. Extract it and copy/overwrite
these files into your Audio-Studio-main repo at matching paths (GitHub web editor:
open each path, replace contents with the matching file below).

## MODIFIED files (overwrite existing)
- app.py
- notifications.py
- tool_pages.py                          (NEW file, but listed here since it's core logic)
- static/js/tools.js
- templates/base.html
- templates/studio.html
- templates/contact.html
- templates/privacy.html
- templates/terms.html
- templates/tools.html

## NEW files (create these paths — they don't exist yet in your repo)
- tool_pages.py
- templates/tool_page.html
- templates/voice_cloning.html
- templates/partials/tool_widgets/transcribe.html
- templates/partials/tool_widgets/convert.html
- templates/partials/tool_widgets/merge.html
- templates/partials/tool_widgets/cutter.html
- templates/partials/tool_widgets/denoise.html
- templates/partials/tool_widgets/voicechange.html
- templates/partials/tool_widgets/videoxtract.html
- templates/partials/tool_widgets/music.html
- templates/partials/tool_widgets/voiceclone.html

## What this patch does (Phase 1 + Phase 2 + Phase 2.5)

**Phase 1 — legal/contact fixes**
- Real working contact form (POST /contact) that emails you via Resend
  (notify_contact_message in notifications.py) — no new env vars needed,
  reuses your existing RESEND_API_KEY / ADMIN_EMAIL.
- Rewrote privacy.html and terms.html — specific to VoxCraft's actual tools
  and data flows, no more "starting template, not legal advice" language.

**Phase 2 — individual tool pages**
- 8 new indexable pages at /tools/<slug> (transcribe, convert, merge, cutter,
  denoise, voice-changer, extract-audio-from-video, ai-music-generator), each
  with real how-it-works/use-cases/tips/FAQ content and FAQPage schema.
- Tool widget markup extracted into templates/partials/tool_widgets/ so the
  /tools hub and the new individual pages share identical, tested UI code.
- tools.js patched to guard against null elements (it assumed all 8 panels
  always existed on the page — would've crashed on single-tool pages).
- Sitemap auto-includes all 8 new URLs via tool_pages.py's TOOL_PAGES dict.

**Phase 2.5 — voice cloning page + Studio rename**
- New dedicated /voice-cloning page, reusing the same clone widget and
  clone_music.js as Studio's Clone tab (no duplicated logic).
- Studio nav renamed to "Voice Studio" (URL kept as /studio per your
  choice), plus a full content section added to studio.html (how it works,
  who uses it, tips, FAQ + schema) that didn't exist before.
- Cross-links added: Studio → voice-cloning, voice-changer FAQ →
  voice-cloning, voice-cloning → Studio/Music/Voice Changer.

## Testing performed
Every file here was validated with:
- Python AST syntax check on app.py / notifications.py / tool_pages.py
- Jinja2 template parse check on every modified/new template
- A real Flask app rendering all 8 tool pages, the /tools hub, studio.html,
  and voice_cloning.html end-to-end (url_for resolution, FAQ schema
  validated as JSON, nav labels, cross-links) — all passed.

No env vars, dependencies, or DB migrations required — this is templates,
routes, and static JS only.
