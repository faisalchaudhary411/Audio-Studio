# VoxCraft — existing tools improvements

## What was improved

### Backend (`audio_tools.py`)
| Tool | Improvements |
|------|----------------|
| **Transcribe** | Urdu in language list; richer result (word_count, duration, simple SRT) |
| **Convert** | Named presets: youtube, social, podcast, edit_master, archive |
| **Merge** | Optional **crossfade** between clips (removes join clicks) |
| **Cutter** | **Auto-trim silence**; split-on-silence helper available |
| **Denoise** | Strength control + **stationary** mode (better for fan/AC) |
| **Voice change** | **Dry/wet** mix; presets: slight_deeper, anon |
| **Video extract** | Optional **start_sec / end_sec** time range |
| **Normalize** | New peak-normalize helper + API |

Whisper still not enabled (needs GPU worker). Google Speech remains the free path; SRT is time-sliced (not word-aligned) until Whisper timestamps exist.

### API (`app.py`)
- Convert accepts `preset`
- Merge accepts `crossfade_ms`
- Denoise accepts `stationary`
- Voice change accepts `dry_wet`
- Video extract accepts `start_sec`, `end_sec`
- New: `POST /api/tools/cutter/auto-trim`
- New: `POST /api/tools/normalize`

### UI widgets
Updated controls for convert presets, merge crossfade, denoise Light/Medium/Strong + stationary, cutter auto-trim mode, video time range, voice dry/wet + presets, transcribe languages + SRT download.

### JS (`static/js/tools.js`)
Wired all new fields; SRT download on transcribe; auto-trim mode; denoise presets; dry/wet label.

## Deploy

```bash
cp audio_tools.py /path/to/repo/
cp app.py /path/to/repo/          # or merge carefully
cp static/js/tools.js /path/to/repo/static/js/
cp templates/partials/tool_widgets/*.html /path/to/repo/templates/partials/tool_widgets/
```

Restart the app.

## Still recommended later (not in this pack)
1. Whisper transcription on GPU worker
2. Waveform UI on cutter
3. Before/after player on denoise
4. Tool chaining buttons (“Send to Denoise / Trim”)
5. New tools: vocal separator, loudness to -14 LUFS, etc.
