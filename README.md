# Studio remaining fixes

## Section labels (fixed)
- Intro / Body / Outro / Full script **only tag the download filename**
- They **do not** insert any text into the script (nothing is spoken)

## Also included
- **Pronunciation fixes** (this browser only) — find → say list
- **Natural pauses between sentences** (checkbox, default on)
- **Batch: Download merged MP3** in addition to ZIP

## Deploy
```bash
cp templates/studio.html /your/repo/templates/
cp static/js/studio.js /your/repo/static/js/
cp tts_engine.py /your/repo/
cp app.py /your/repo/
```
Hard-refresh browser.
