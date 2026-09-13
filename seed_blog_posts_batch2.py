"""
seed_blog_posts_batch2.py — second batch of blog posts (2/month cadence),
same pattern as seed_blog_posts.py.

WHY THESE TWO TOPICS: both are written to reinforce the SEO landing pages
that just got a real route (see seo_landing_page() in app.py) — each post
links to the specific language page(s) it's about, and its related_tool
CTA now routes through that landing page rather than straight to Studio
(see the BLOG_TOOL_LINKS update in app.py). The goal is a proper topic
cluster: search query -> blog post -> landing page -> Studio, each hop
reinforcing the next rather than every page competing for the same click.

USAGE (same as seed_blog_posts.py — run once, from the repo root):
    python3 seed_blog_posts_batch2.py

Safe to re-run: dedupes by title, same as the original script.
"""
import time
import datetime as dt

import persistence

AUTHOR = "VoxCraft Team"
TODAY = dt.datetime.now().strftime("%Y-%m-%d")

POSTS = [
    {
        "title": "How to Convert Hindi Text to Speech: Free AI Voices in 2026",
        "category": "Tutorials",
        "related_tool": "hindi-tts",
        "tags": ["hindi", "tts", "tutorial", "ai-voice"],
        "excerpt": "A practical guide to generating natural Hindi narration with free AI text-to-speech — what actually affects pronunciation quality, and a step-by-step workflow that avoids the most common mistakes.",
        "body": """Hindi text-to-speech has gotten dramatically better over the last couple of years, but most people's first attempt still comes out sounding slightly off — not broken, just not quite right. Usually that's not a limitation of the AI voice itself; it's a handful of avoidable mistakes in how the script gets prepared.

## Why Hindi TTS quality varies so much between tools

Hindi pronunciation depends heavily on the script it's reading. A model trained mostly on English and fine-tuned for Hindi as an afterthought tends to mishandle conjunct consonants, nasalization, and words borrowed from Sanskrit, Urdu, or English — the exact spots a native listener notices immediately. A tool built with real Devanagari-script training data handles these far more reliably, which is why script choice (see below) matters more than most people expect.

## Step-by-step: generating clean Hindi narration

1. **Write in Devanagari script, not Romanized Hindi.** Typing Hindi in Latin letters ("aap kaise hain") forces the model to guess at pronunciation from spelling patterns that don't map cleanly onto Hindi phonetics. Native script (आप कैसे हैं) gives the model the actual phonetic information it needs — this single change fixes more pronunciation issues than anything else on this list.
2. **Preview a short line before committing a full script.** Voices differ in pacing and tone; a 10-second test tells you more than reading documentation ever will.
3. **Break long scripts into shorter sections.** A single giant paragraph gives the model more places to lose its footing on pacing and emphasis. Natural paragraph breaks, matching how you'd actually pause while speaking, produce steadier results.
4. **Flag names, numbers, and mixed-language phrases separately.** Proper nouns and English loanwords embedded in Hindi text are consistently the hardest thing for any TTS system to get right — test these in isolation before trusting them in a full read.
5. **Listen to the whole thing before publishing.** Even a strong TTS engine will occasionally land on an odd emphasis or a mispronounced word — a full listen-through catches this before your audience does.

## When free tiers are (and aren't) enough

Free-tier Hindi TTS is usually fine for short scripts, testing a voice before a bigger project, or occasional use. If you're producing longer-form content regularly — a weekly video series, an audiobook chapter, a course — character limits and daily generation caps start to matter, and that's the point where a paid tier earns its cost in saved re-recording time rather than raw minutes of audio.

## A quick troubleshooting checklist

If a specific word keeps coming out wrong no matter what you try, the fastest fix is often just rephrasing around it — swapping in a more common synonym costs nothing and usually resolves rare-word mispronunciation faster than fighting with spelling variants. If pacing feels off on a whole section, check whether that section is a single unbroken block of text; splitting it usually helps more than adjusting the speed setting alone.

Hindi TTS has reached the point where, for most everyday uses — YouTube narration, e-learning content, quick voiceovers, accessibility readouts — a careful few minutes of script prep is genuinely enough to get a natural-sounding result without hiring a voice artist or recording it yourself.""",
    },
    {
        "title": "Multilingual YouTube Voiceover: Urdu, Hindi, Punjabi and Bengali in One Workflow",
        "category": "Guides",
        "related_tool": "multilingual-voiceover",
        "tags": ["multilingual", "youtube", "voiceover", "south-asian-languages"],
        "excerpt": "A practical workflow for creators producing the same video, or the same channel, across Urdu, Hindi, Punjabi and Bengali — without redoing your entire process for each language.",
        "body": """Producing content in one South Asian language is a solved problem for most creators now. The harder version — publishing across two, three, or four of these languages without your workflow falling apart — is where most channels either burn out or just never start.

## Why "one language, then repeat" doesn't scale

The instinct is to fully finish a video in one language, then start over from scratch in the next. That works for a single extra language. It stops working past that, because every re-record, re-edit, and re-review cycle multiplies your total production time almost linearly — four languages can easily mean four times the work, not a modest bump.

## A workflow that scales better

1. **Write and lock the script in one language first**, then translate — don't write four scripts independently. A single source script keeps your message, pacing, and structure consistent, and makes it obvious later if a translation drifted from the original meaning.
2. **Generate a short test line in each target language before the full script.** Urdu, Hindi, Punjabi and Bengali each have their own pronunciation quirks — catching an issue on one sentence is a lot cheaper than discovering it after generating fifteen minutes of narration.
3. **Keep scripts in native script, not Romanized transliteration**, in every language. This matters even more across multiple languages, since inconsistent transliteration habits compound into inconsistent output quality between your videos.
4. **Generate narration for all languages before moving to editing.** Batch the TTS step across languages rather than interleaving it with editing — it's easier to compare pacing and tone across versions when they're generated back to back.
5. **Reuse your visual edit across language versions where the content allows it.** If your B-roll, graphics, and pacing aren't language-dependent, one edited timeline with swapped audio tracks is far faster than cutting each language version from scratch.

## Language-specific notes worth knowing

- **Urdu** narration benefits the most from getting the script right the first time — Nastaliq script gives noticeably better pronunciation than any Romanized alternative.
- **Hindi** shares some of the same rules as Urdu; Devanagari script input matters just as much here for names, loanwords, and conjunct consonants.
- **Punjabi** content often mixes in Hindi or Urdu-adjacent vocabulary depending on region and audience — a short test line matters more here than in most languages, since word choice affects pronunciation more than usual.
- **Bengali** has its own distinct script and phonetic patterns — treat it as its own test pass rather than assuming what worked for Hindi will transfer directly.

## Keeping four languages from becoming four separate channels' worth of work

The realistic goal isn't zero extra effort per language — it's making each additional language cost a fraction of the first one, not a repeat of it. A shared source script, a consistent script-preparation habit across languages, and batching the narration step rather than fully re-doing your process per language is what actually makes multilingual publishing sustainable instead of a one-time experiment you abandon after two videos.""",
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
        print(f"\nNothing to add — all {skipped} post(s) already exist.")


if __name__ == "__main__":
    main()
