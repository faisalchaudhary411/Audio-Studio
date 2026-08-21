# VoxCraft — pronunciation dictionary + expression presets

Same repo structure — overwrite these paths. app.py is built on the
correctly-merged file (CLONE_CHAR_LIMIT = 1400 preserved — confirmed
below, and re-tested against this exact file, not an earlier draft).

## Files
- app.py (MODIFIED)
- persistence.py (MODIFIED — new pronunciation_dict table)
- tts_engine.py (MODIFIED — substitution engine + 5 new expression presets)
- templates/studio.html (MODIFIED — documents new expression tags)
- templates/admin/pronunciation.html (NEW — admin CRUD page)
- templates/admin/dashboard.html (MODIFIED — new dashboard card/link)

## A note on how this was built

Made the same process mistake as the previous batch — built today's
changes on a stale tracked copy instead of your actual merged app.py.
Caught it again before packaging (checked for CLONE_CHAR_LIMIT = 1400 and
found 2000). Extracted today's changes as an isolated diff (confirmed
exactly 4 changes: one import line, the new admin_pronunciation route, and
two generation call-site edits — nothing else touched), and reapplied them
onto your correct file. Re-ran the full test suite against that exact
file before packaging.

## What this adds

**1. Pronunciation dictionary (global find/say substitution)**
A new admin page at /admin/pronunciation lets you define word
substitutions — e.g. "Nginx" -> "Engine-X", "QalamStudio" -> "Kuh-lum
Studio" — applied to Studio's Single and Batch text-to-speech generation
before the text reaches edge-tts. NOT applied to voice previews (those use
fixed sample text).

Technical notes:
- No DB migration needed — new pronunciation_dict table auto-creates on
  first run, same pattern as blogs/announcements (JSON blob storage).
- Whole-word matched (regex \\b boundaries) so "Find: Go" won't corrupt
  "Google" or "Gopher".
- Case-insensitive by default; a "match case exactly" checkbox is
  available per entry for the rare case where capitalization matters.
- When entries overlap (e.g. "York" and "New York" both defined), the
  longer/more specific entry is applied first so it isn't pre-empted by
  the shorter one.
- This is deliberately plain text substitution, not SSML phoneme tags —
  edge-tts (the library wrapping Microsoft Edge's free read-aloud
  feature) doesn't expose phoneme-level pronunciation control the way the
  full Azure Cognitive Services SSML surface does. Respelling the word is
  the reliable lever available, and it has the side benefit of working
  through the gTTS fallback path too, since that's plain text as well.

**2. Expression presets (5 new markup tags)**
Added [excited], [serious], [calm], [cheerful], [sad] to Studio's existing
markup system, alongside the original [pause]/[strong]/[em]/[slow]/[fast]/
[high]/[low]/[whisper] tags. Each new tag maps to a tested combination of
rate/pitch/volume — e.g. [excited] = faster + higher pitch + louder,
[sad] = slower + lower pitch + quieter.

Important honesty note (also flagged in-app, in the admin panel copy, and
in Studio's tips section): these are NOT true emotional synthesis. edge-tts
doesn't expose Azure's mstts:express-as styles (genuine "cheerful"/"sad"
voice acting) — what's here approximates a feeling through pacing, pitch,
and loudness only. It noticeably changes delivery; it won't sound like a
different performance choice the way a real Azure Speech subscription or
a model like ElevenLabs could. If genuine emotional styles are wanted
later, that requires switching TTS backends, not extending this one.

## Testing performed
- Python AST syntax check on all 3 modified Python files, run against the
  exact final merged app.py.
- Correctness tests on the substitution engine: case-insensitive matching,
  word-boundary safety (doesn't corrupt "Google" when correcting "Go"),
  longest-match-first for overlapping entries ("New York" vs "York"),
  and graceful handling of empty/malformed entries.
- Full DB round-trip test against a real SQLite database: admin create ->
  reload -> the exact substitution the generation pipeline would apply ->
  admin update -> admin delete, all verified against actual persisted data.
- Rendered admin/pronunciation.html in both list view and edit-mode
  (confirmed correct prefill of find/say/match_case), rendered
  admin/dashboard.html (confirmed the new card and link), and rendered
  studio.html (confirmed all 5 new expression tags appear in the
  cheatsheet).
- Regression-tested the original 8 markup tags (pause/strong/em/slow/
  fast/high/low/whisper) to confirm zero behavior change from adding the
  5 new ones.
- Confirmed both generation call sites (single + batch) are correctly
  wired, and confirmed the voice-preview route was deliberately left
  unwired (previews use fixed sample text, not user-submitted words).
