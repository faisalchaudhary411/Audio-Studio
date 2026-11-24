# VoxCraft SEO Growth Changes — 24 Nov 2026

## What was done (Option A)

### 1. New high-intent landing pages (Speech-to-Text)
These match the exact queries already showing in your Search Console (positions 60–90):

| New URL | Targets |
|---------|---------|
| `/urdu-speech-to-text` | urdu speech to text, speech to text urdu, urdu voice to text |
| `/hindi-speech-to-text` | hindi speech to text, speech to text hindi |
| `/punjabi-speech-to-text` | punjabi speech to text, speech to text punjabi |

All three:
- Have unique title, meta, H1, intro, steps, use cases, FAQ
- Primary CTA goes **directly to the Transcribe tool** (not Studio)
- Cross-link to each other + WhatsApp voice-note tool + TTS pages
- Are automatically included in `/sitemap.xml`

### 2. Stronger internal linking
Updated related links on:
- urdu / hindi / punjabi text-to-speech pages
- how-to-create-youtube-voiceover
- text-to-speech-for-youtube
- best-urdu / best-hindi text-to-speech pages

So traffic that lands on TTS pages can flow to STT (and vice versa).

### 3. Transcribe tool page title/meta improved
Old title was narrow ("Urdu & Hindi Speech to Text").
New title: **"Speech to Text Free — Urdu, Hindi, Punjabi & English | VoxCraft"**
Better match for the broader queries Google is already showing you.

### 4. Proper 404 page
`templates/404.html` added with:
- noindex
- helpful links to Studio, Tools, Speech-to-Text, and the new language STT pages
- Better UX than a plain text 404

### 5. CTA routing fix in `app.py`
Speech-to-text landings and the noise page now send the main button to the correct tool instead of always to Studio.

---

## Files changed
- `seo_pages.py` — 3 new pages + related_links updates
- `tool_pages.py` — transcribe title / meta / h1
- `app.py` — smarter CTA routing for SEO pages
- `templates/404.html` — new

---

## What YOU must do after deploy (critical)

1. **Deploy** these files to production.
2. Open Google Search Console → **Sitemaps** → resubmit `https://voxcraft.site/sitemap.xml`
3. **URL Inspection** → request indexing for these new pages (one by one):
   - https://voxcraft.site/urdu-speech-to-text
   - https://voxcraft.site/hindi-speech-to-text
   - https://voxcraft.site/punjabi-speech-to-text
   - https://voxcraft.site/tools/transcribe-audio-to-text
   - https://voxcraft.site/how-to-create-youtube-voiceover
4. Also request indexing for any important pages that still show "Discovered – currently not indexed".
5. Fix the 6 × 404s reported in Coverage (check which old URLs they are — often old blog or tool URLs). Add 301 redirects if needed.

---

## Realistic expectations

- These changes alone will **not** create hundreds of visitors overnight.
- They give Google clean, keyword-matched pages for queries you already appear on (positions 60–90).
- Combined with **distribution** (Reddit, Quora, Facebook groups, careful new YouTube) you can move from 3–4 users/day toward 30–100+ over the next 4–8 weeks if you stay consistent.

Technical SEO is now in a good place. The bottleneck is authority + distribution.
