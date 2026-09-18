"""
seed_transcription_post.py — one-time script to publish a supporting blog
post for the newly-updated Urdu/Hindi-first transcribe tool page.

WHY THIS EXISTS: same pattern as seed_blog_posts.py — writes directly
through persistence.py so you don't have to paste a long post through the
admin UI on a phone. Safe to re-run; it checks the title first and skips
if the post already exists.

USAGE (run once, on the VPS, from the repo root):
    python3 seed_transcription_post.py

After running, check /admin/blog, then spot check /blog and the post's
own URL on the live site.
"""
import time
import datetime as dt

import persistence

AUTHOR = "VoxCraft Team"
TODAY = dt.datetime.now().strftime("%Y-%m-%d")

POSTS = [
    {
        "title": "How to Transcribe Urdu or Hindi Audio to Text for Free",
        "category": "Tutorials",
        "related_tool": "transcription",
        "tags": ["urdu", "hindi", "transcription", "speech to text", "tutorial"],
        "excerpt": "A practical guide to turning Urdu and Hindi recordings — interviews, lectures, voice notes — into text, without paying for a transcription service or typing it out by hand.",
        "body": """Most free transcription tools treat Urdu and Hindi as an afterthought — buried at the bottom of a language list built mainly for English. That makes a simple task harder than it needs to be: you either mis-select a distant locale and get garbled output, or give up and type the whole thing out by hand.

## Why language selection matters more for Urdu and Hindi

Automatic speech recognition works by matching audio against a language model. Pick the wrong one — or leave it on auto-detect for a recording with regional accents or mixed Urdu-English speech — and accuracy drops fast, even if the underlying engine handles the language well when told what it's listening to. Selecting Urdu or Hindi explicitly, rather than trusting auto-detect, is the single biggest accuracy lever you have.

## Step-by-step: transcribing Urdu or Hindi audio

1. **Record or export clean audio first.** A voice memo, a Zoom recording, a WhatsApp voice note — any of these work, but background noise (traffic, fans, crosstalk) hurts accuracy more than almost anything else.
2. **Upload the file.** WAV, MP3, M4A, OGG and FLAC are all supported, up to 15MB per file.
3. **Select the language explicitly.** Choose Urdu or Hindi from the dropdown rather than leaving it on auto-detect.
4. **Transcribe and review.** Read the output against the audio for names, numbers, and technical terms — automatic transcription gets the gist right almost always, but proper nouns are where it's most likely to guess wrong.
5. **Download or copy the text**, then take it into whatever you're actually building — an article, subtitles, study notes, meeting minutes.

## Where this actually helps

- **Podcasters and YouTubers** turning an Urdu or Hindi episode into a blog post or show notes without re-typing everything.
- **Students** converting a recorded lecture into searchable, highlightable text.
- **Journalists** getting a rough interview transcript to quote from, then checking exact wording against the audio for anything going in print.
- **Anyone with a backlog of voice notes** they've been meaning to turn into actual notes.

## Common mistakes that hurt accuracy

- **Leaving it on auto-detect** for Urdu or Hindi audio instead of selecting the language directly.
- **Transcribing noisy audio as-is** — if a recording has a lot of background noise, running it through a denoise pass first usually improves the transcript noticeably.
- **Trusting every proper noun and number automatically.** Names, places, and figures are worth a manual check even when the rest of the transcript reads cleanly.
- **Assuming perfect speaker separation** in recordings with multiple people talking — overlapping speech reduces accuracy regardless of language, and the transcript won't reliably label who said what.

## What to do next

Once you have a transcript, it's just text — copy it into a doc, drop it into an editor for subtitles, or use it as the starting script for a text-to-speech voiceover in a different language. Transcription and text-to-speech are opposite ends of the same workflow: audio to text, or text to audio, depending on which direction your project needs to go.""",
    },
]


def main():
    existing = persistence.load_blogs()
    by_title = {(p.get("title") or "").strip().lower(): p for p in existing}

    added = 0
    skipped = 0
    for i, post in enumerate(POSTS):
        key = post["title"].strip().lower()
        if key in by_title:
            print(f"SKIP (already exists): {post['title']}")
            skipped += 1
            continue
        new_post = {
            "id": str(int(time.time() * 1000) + i),
            "title": post["title"],
            "category": post["category"],
            "tags": post.get("tags", []),
            "excerpt": post["excerpt"],
            "body": post["body"],
            "author": AUTHOR,
            "updated_date": TODAY,
            "related_tool": post["related_tool"],
            "date": TODAY,
            "published": True,
        }
        existing.insert(0, new_post)  # matches admin_blog's "create" behavior — newest first
        added += 1
        print(f"ADD: {post['title']}")

    if added:
        persistence.save_blogs(existing)
        print(f"\nDone — added {added}, skipped {skipped}.")
    else:
        print(f"\nNothing to add — post already exists.")


if __name__ == "__main__":
    main()
