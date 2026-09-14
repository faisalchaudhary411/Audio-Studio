"""
generate_voice_previews.py — one-time batch job to pre-render a short
preview .mp3 for every voice in voices.py, so the /voices page's play
buttons actually work instead of only the 3 that already exist.

Run this FROM THE PROJECT ROOT on the VPS (same place app.py lives),
with the normal venv/deps active, since it imports tts_engine.py and
voices.py directly and needs real network access to Microsoft's
edge-tts endpoint:

    python3 generate_voice_previews.py

Safe to re-run: it skips any file that already exists, so if it gets
interrupted partway (network hiccup, VPS restart) just run it again
and it'll pick up where it left off. Delete a specific .mp3 from
static/audio/previews/ if you ever want to force-regenerate just that
one voice.
"""

import os
import time

from voices import VOICES, default_preview_text
from tts_engine import tts_dispatch

OUT_DIR = os.path.join("static", "audio", "previews")
DELAY_SECONDS = 0.5  # be polite to the free edge-tts endpoint between calls


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    jobs = []
    for language, voice_map in VOICES.items():
        for label, voice_id in voice_map.items():
            slug = voice_id.lower()
            out_path = os.path.join(OUT_DIR, f"{slug}.mp3")
            jobs.append((language, label, voice_id, out_path))

    total = len(jobs)
    skipped = 0
    done = 0
    failed = []

    print(f"{total} voices in catalogue, writing to {OUT_DIR}/")

    for i, (language, label, voice_id, out_path) in enumerate(jobs, 1):
        if os.path.exists(out_path):
            skipped += 1
            continue

        text = default_preview_text(language)
        print(f"[{i}/{total}] {language} — {label} ({voice_id}) ...", end=" ", flush=True)

        try:
            audio = tts_dispatch(text, voice_id)
            with open(out_path, "wb") as f:
                f.write(audio)
            done += 1
            print(f"ok ({len(audio)} bytes)")
        except Exception as e:
            failed.append((language, label, voice_id, str(e)))
            print(f"FAILED — {e}")

        time.sleep(DELAY_SECONDS)

    print()
    print(f"Done. {done} generated, {skipped} already existed, {len(failed)} failed.")
    if failed:
        print("\nFailed voices (re-run the script to retry these):")
        for language, label, voice_id, err in failed:
            print(f"  - {language} / {label} ({voice_id}): {err}")


if __name__ == "__main__":
    main()
