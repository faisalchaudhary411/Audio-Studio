# VoxCraft — developer API (POST /api/v1/tts) with metered API keys

Same repo structure. app.py built on the correctly-merged base —
CLONE_CHAR_LIMIT = 1400 confirmed intact.

## Files
- app.py (MODIFIED)
- persistence.py (MODIFIED — 2 new tables)
- notifications.py (MODIFIED — new email function)
- api_keys.py (NEW)
- templates/admin/api_keys.html (NEW)
- templates/admin/dashboard.html (MODIFIED — new card/link)

## What this is

A separate, metered, paid developer API — distinct from the browser app
licenses in licensing.py. A customer pays through your existing
Freemius/manual-PKR flow for a plan with a monthly character allowance,
you issue them a key at /admin/api-keys, and they call:

    curl -X POST https://voxcraft.site/api/v1/tts \
      -H "Authorization: Bearer vox_live_..." \
      -H "Content-Type: application/json" \
      -d '{"text": "Hello world", "voice_id": "en-US-AvaNeural"}' \
      --output speech.mp3

GET /api/v1/voices (also key-authenticated) lists every valid voice_id so
a developer doesn't need separate docs just to get started.

## Why fixed-quota, not true metered billing

Real usage-based billing (ElevenLabs' actual model — pay per character,
automatically charged) needs a payment gateway built for metered
subscriptions. Freemius (fixed-price) and manual PKR transfers aren't
that. This gives customers a monthly character allowance instead — feels
metered to them (they see a usage bar, get blocked at the cap), sells
through infrastructure you already have. Self-serve signup can replace
the manual admin-issues-the-key step later without touching how the API
itself works.

## Security & correctness decisions worth knowing about

**Keys are hashed at rest (SHA-256), never stored raw.** Same principle
as a password — a full database leak doesn't hand out working keys. The
raw key is shown exactly once, at creation, in the admin panel's "copy it
now" box, and emailed to the customer. If it's lost, a new key has to be
issued; there's no "forgot my key" recovery, by design.

**Usage counting is genuinely safe under your 2-gunicorn-worker setup.**
This mattered enough to build and prove separately before writing the API
endpoint on top of it. Key metadata (customer info, plan, quota — rarely
changes) lives in one table using the same simple pattern as your blog
posts. The character-usage counter (written on literally every API call)
lives in a SEPARATE table using the same atomic BEGIN IMMEDIATE
transaction your license-key activation already relies on. I ran an
actual concurrency stress test — 20 threads simultaneously bumping one
key's counter — and confirmed the final total was exactly correct, not
silently undercounted the way the old browser-usage tracking used to be
before it was fixed (see usage_tracking.py's own docstring for that
history).

**Quota is only deducted on successful generation.** A bad voice_id, a
malformed request, or a TTS engine error costs the customer nothing —
mirrors the existing _bump_monthly_chars() pattern for the free tier.

**Per-request cap of 5,000 characters** (API_MAX_CHARS_PER_REQUEST in
app.py) — mainly so one oversized request can't be the only thing
standing between a customer and their entire month's quota in one shot.
Easy to adjust if you want it higher/lower.

## What's NOT built yet (intentionally out of scope for this round)
- Self-serve signup/checkout for API plans (currently admin-issued after
  manual payment confirmation, same as your existing Pro/Pro+ flow)
- A public API documentation page (the quick-start curl example is in the
  key-delivery email for now)
- Support for other tools beyond TTS (transcription, voice cloning, etc.)
  through the API — you specifically asked for TTS first

## Testing performed
- Python AST syntax check on all 4 modified/new Python files, against the
  exact final merged app.py.
- Standalone api_keys.py module test against a real SQLite DB: key
  creation, hash correctness, raw-key-not-persisted-anywhere verification,
  lookup by correct/incorrect/malformed keys, quota pre-check math,
  usage bump + resulting quota math, revoke/unrevoke/delete.
- A dedicated concurrency stress test BEFORE building the API on top of
  it: 20 threads simultaneously bumping one key's usage counter, confirmed
  the final total was exactly correct (proving the transaction actually
  prevents the race condition, not just trusting the pattern by
  inspection) — this caught a real bug (a missing @contextlib.contextmanager
  decorator) that a syntax check alone would never have caught.
- Full HTTP-level test via Flask's real test client against the actual
  /api/v1/tts and /api/v1/voices routes: missing auth (401), invalid key
  (401), revoked key (403), missing text (400), invalid voice_id (400),
  a valid request succeeding with correct audio bytes and correct
  X-Quota-* headers, exceeding quota (429) with a clear error body, and
  reactivation restoring access.
- Rendered admin/api_keys.html with real data and confirmed the one-time
  raw-key display box and the usage progress bar both show correct values.
