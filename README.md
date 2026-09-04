# Studio + Voice Cloning improvements

## TTS Studio
- Remember last language/voice (localStorage)
- Preview stock line OR **Preview my first line**
- SSML **insert buttons** (pause, strong, em, slow, fast, calm, serious)
- Optional section labels (Intro / Body / Outro)
- Mixed Urdu/Hindi + Roman script **tips**
- Long-script budget warning
- Export format + **normalize loudness** option
- After generate: **Send to Trim / Denoise / Merge**
- API: preview accepts custom text; generate applies normalize when requested

## Voice Cloning
- Ideal reference **checklist** + permission rule on page
- **Generate consent** checkbox required before run
- Reference **quality warnings** (duration, quiet, clipping) on upload
- Progress steps (Upload → Queue → Generating)
- Result: Send to Trim / Denoise / Merge
- Chunk stitch uses **crossfade** instead of hard cuts

## Deploy
```bash
cp templates/studio.html /your/repo/templates/
cp templates/partials/tool_widgets/voiceclone.html /your/repo/templates/partials/tool_widgets/
cp static/js/studio.js /your/repo/static/js/
cp static/js/clone_music.js /your/repo/static/js/
cp app.py /your/repo/
cp clone_engine.py /your/repo/
cp audio_tools.py /your/repo/   # needed for normalize()
```
Hard-refresh browser after deploy.
