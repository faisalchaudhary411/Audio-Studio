# VoxCraft — header, homepage, hub restructure & PKR pricing fix

Same folder structure as your repo — extract and overwrite these paths. All files
listed here are MODIFICATIONS to existing files (nothing new in this batch).

## Files
- app.py
- persistence.py
- static/css/style.css
- templates/tools.html
- templates/studio.html
- templates/pricing.html
- templates/upgrade.html
- templates/landing.html
- templates/admin/limits.html

## What changed and why

**Header (mobile)**
- Hid the "Open Voice Studio" nav pill on mobile — it duplicated the "Voice
  Studio" link already in the hamburger menu and was crowding the header
  next to the notification bell (visible in your screenshot). Top row on
  mobile is now just bell + hamburger.

**Homepage (landing.html)**
- Removed a false claim in the Pricing section — it said "no tiers to
  compare" while the site clearly has Free/Pro/Pro+ tiers. Rewritten to
  describe the actual tiers.
- Added a proper "Audio toolkit" section — the homepage previously never
  mentioned the Tools suite (transcribe, convert, merge, etc.) at all.

**Tools hub → directory (tools.html + app.py's tools_hub route)**
- Per your call: /tools is now a lightweight directory of 8 cards linking
  to each tool's own dedicated /tools/<slug> page, instead of embedding
  every tool's full working widget directly on the hub. This gives search
  traffic (and anyone browsing) a real reason to land on and stay on the
  specific page that matches what they need, instead of the hub already
  answering everything on one URL.
- tools.js is no longer loaded on the hub page (nothing there needs it now)
  — still loaded on the individual tool pages as before.

**Studio Clone/Music tabs → preview cards (studio.html)**
- Same restructure applied to Studio: the Clone and Music tabs no longer
  embed the full working widgets — they're now short preview cards with a
  button linking to /voice-cloning and /tools/ai-music-generator
  respectively, which is where the real Pro+ tools now live.
- Removed the now-unused clone_music.js include and a dead
  window.VOXCRAFT_HAS_CLONE_MUSIC global that nothing referenced.

**PKR pricing — real bug, not just a display issue**
- Pro+ had NO PKR price field at all in the system — only Pro did. The
  manual-payment page (used by Pakistani customers paying via
  EasyPaisa/JazzCash/bank) never showed ANY amount to send, for either
  plan — it only had hardcoded "$3/mo" / "$6/mo" labels with no connection
  to the actual configured prices.
- Added PRO_PLUS_PRICE_PKR / PRO_PLUS_PRICE_LABEL / PRO_PLUS_PRICE_USD_LABEL
  to persistence.py defaults (mirroring Pro's existing PRO_PRICE_PKR /
  PRO_PRICE_LABEL), plus a new PRO_PRICE_USD_LABEL for Pro — all editable
  in /admin/limits now.
- /upgrade now shows a prominent "Amount to send: Rs ___" box that updates
  live based on which plan (Pro vs Pro+) is selected.
- /pricing now shows both the USD price and the PKR manual-payment amount
  for each paid plan.

## Defaults used (please verify/adjust in /admin/limits)
- Pro: $3/mo · 840 PKR (unchanged, already your existing default)
- Pro+: $6/mo · 1680 PKR (NEW — I set this at the same 2x ratio as Pro's
  USD-to-PKR relationship since there was no existing Pro+ PKR value to
  preserve; double-check this is the amount you actually want to charge)

## Testing performed
- Python AST syntax check on app.py and persistence.py
- Jinja2 template parse check on all 6 touched templates
- A real Flask app rendering: the new tools directory (confirmed 8 cards,
  no leftover tab buttons), studio.html (confirmed clone/music widgets are
  gone and replaced with links), pricing.html (confirmed PKR shows for
  both plans), upgrade.html (confirmed "Rs 840"/"Rs 1680" shows correctly
  based on selected plan), landing.html (confirmed false claim removed and
  Tools section links correctly), and admin/limits.html (confirmed new
  fields render) — all passed.
