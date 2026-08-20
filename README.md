# VoxCraft — notification banner: toast redesign + stale-cache fix

3 files, same repo structure — overwrite these paths.

## Files
- app.py
- static/css/style.css
- static/js/notifications.js

## What changed

**Likely root cause of "banner blank on Pro/Pro+ (same browser)"**
`/api/announcements` never sent `Cache-Control: no-store`. Testing Free,
then activating Pro on the SAME browser/device shortly after, could mean
the second page load served a stale cached copy of that GET response
instead of hitting the server again — the bell badge (computed differently,
from localStorage vs. the fetched list) still worked, but the banner's
content came from that same possibly-stale fetch. Added `no-store` so
every page load always gets the current announcement list. If this was
actually the cause, it's fixed now; if the banner still misbehaves after
deploying, it points to something else and I'll dig further.

**Banner redesign — was a sticky in-flow bar, now a toast**
- Was: `position:static`, sat in normal page flow pushing content down,
  stayed until manually clicked closed.
- Now: `position:fixed`, centered near the top, slides down into view with
  a spring-ish easing, and auto-dismisses itself after 6 seconds (still
  closeable early via the × button). Doesn't push page content anymore.
- The old `has-announce-banner` body class this used to toggle had no CSS
  rule attached to it anyway (dead code) — removed.

## Testing performed
- Python AST syntax check on app.py
- `node --check` on notifications.js
- A real jsdom DOM simulation: rendered the bell + banner markup, called
  the actual notification functions, and verified: bell badge shows
  unread count, banner text populates correctly, the `is-visible` class
  (which drives the slide-in transition) gets applied, the toast
  auto-dismisses after 6s, and the dismissed announcement ID is correctly
  written to localStorage afterward — all confirmed working end-to-end.
