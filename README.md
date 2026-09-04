# New practical tools (5)

| Slug | URL path | What it does |
|------|----------|--------------|
| normalize-audio-volume | /tools/normalize-audio-volume | Peak normalize to target dBFS |
| adjust-audio-volume | /tools/adjust-audio-volume | Fixed gain ±12 dB |
| change-audio-speed | /tools/change-audio-speed | 0.5×–2× speed (pitch shifts with speed) |
| fade-audio | /tools/fade-audio | Fade in / fade out |
| split-audio-by-silence | /tools/split-audio-by-silence | Split long file at pauses (max 20 parts) |

## Deploy
```bash
cp audio_tools.py app.py tool_pages.py /your/repo/
cp static/js/tools.js /your/repo/static/js/
cp templates/partials/tool_widgets/{normalize,volume,speed,fade,split}.html /your/repo/templates/partials/tool_widgets/
```

Hard-refresh. New pages appear on /tools hub and sitemap automatically via TOOL_ORDER.

## Notes
- Speed change is resample-based (pitch moves with speed) — practical for Shorts, not studio time-stretch.
- Split uses pydub silence detection; noisy rooms may need Denoise first.
