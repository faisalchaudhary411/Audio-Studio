# Voice Changer fix

## Problems fixed
1. **Dual voice (original + effect)** — broken dry/wet used `overlay()`, which layered two full voices. Replaced with sample-level blend; presets always run at 100% effect only.
2. **Weak effects** — stronger robot modulation, clearer echo (2 taps), better preset pitch amounts (slight_deeper −4, anon −6 + mild ring, deep −7, chipmunk +7).

## Deploy
```bash
cp audio_tools.py /your/repo/
cp static/js/tools.js /your/repo/static/js/
cp templates/partials/tool_widgets/voicechange.html /your/repo/templates/partials/tool_widgets/
```
Hard-refresh the browser.

## How to use
- **Presets** (Slight deeper, Anon, Chipmunk, Deep): full effect, no mix slider.
- **Pitch Shift / Robot / Echo**: adjust controls; Effect amount at 100% = only processed voice.
