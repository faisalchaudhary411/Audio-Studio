# Tool fixes (critical)

## Bugs fixed

1. **tools.js SyntaxError** — duplicate `const denoiseStrength` broke *all* tools (nothing ran).
2. **Merge multi-file picker** — restored `+ Add files` button, hidden multi input, and `merge-file-list` (JS requires these IDs).
3. **Convert / all tools file accept** — broadened to `audio/*` + explicit MIME types so WAV and other formats appear in the system picker on mobile and desktop.
4. **Merge crossfade** — UI + API still supported; gap/crossfade labels wired.
5. **Cutter auto-trim** — mode button + API route kept; split field id aligned (`cutter-split`).

## Deploy (overwrite previous broken pack)

```bash
cp audio_tools.py /your/repo/
cp app.py /your/repo/
cp static/js/tools.js /your/repo/static/js/
cp templates/partials/tool_widgets/*.html /your/repo/templates/partials/tool_widgets/
```

Hard-refresh the browser (Ctrl+Shift+R) so the new tools.js loads.

## Quick test

1. Merge: Add files twice → list shows 2+ files → Merge works
2. Convert: pick a .wav → converts
3. Any other tool: button responds (no silent failure from JS error)
