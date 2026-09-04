# Tools round 2

## Fixes
1. **Speed** — keeps pitch by default (librosa time-stretch). Optional checkbox to allow pitch shift.
2. **Split by silence** — **Download all as ZIP** plus individual parts.

## New tools
- Reverse audio
- Stereo → mono
- Loop (2–10×)
- Simple EQ (bass / treble)

## Tools library redesign
- Grouped sections (Speech, Edit, Volume, Format, Time, Create)
- Compact cards, shorter copy
- Less long explanatory page content

## Deploy
```bash
cp audio_tools.py app.py tool_pages.py /your/repo/
cp static/js/tools.js /your/repo/static/js/
cp static/css/style.css /your/repo/static/css/
cp templates/tools.html /your/repo/templates/
cp templates/partials/tool_widgets/*.html /your/repo/templates/partials/tool_widgets/
```
Hard-refresh.
