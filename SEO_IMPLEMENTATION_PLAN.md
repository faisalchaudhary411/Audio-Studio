# VoxCraft SEO Implementation Plan
**Date:** 2026-09-15  
**Domain:** https://voxcraft.site  
**Goal:** Rank for 30–40 high-intent keywords across TTS + 18 free audio tools, compete with ElevenLabs / TTSMaker / Adobe Podcast / Narakeet / Fliki / etc., and become the default free multilingual (especially South-Asian) audio toolkit.

---

## 1. What Was Already Strong (No major rebuild needed)

- Unique titles + meta descriptions on every tool & SEO landing page
- Dedicated indexable tool pages (not just tabs)
- 10 SEO landing pages (Urdu/Hindi/Punjabi/Bengali/Tamil/Telugu TTS + YouTube workflows)
- Dynamic sitemap.xml + robots.txt
- Canonical tags, Open Graph, Twitter Cards
- FAQPage schema on tool + SEO pages
- SoftwareApplication + Organization schema on homepage
- Admin panel to edit titles/metas without code
- Blog infrastructure + seed posts
- Plausible analytics ready (env-gated)
- Google Search Console verification meta already in base.html

## 2. Code Fixes Implemented in This Pass

| Fix | File(s) | Status |
|-----|---------|--------|
| Google Analytics 4 support | `templates/base.html`, `app.py` | Done — set `GA4_MEASUREMENT_ID=G-XXXXXXXX` |
| Empty avatar `alt=""` → proper alt | `templates/base.html` | Done |
| Semantic breadcrumb `<nav>` + ARIA | `templates/tool_page.html` | Done |
| BreadcrumbList schema | `templates/tool_page.html` | Done |
| HowTo schema on every tool page | `templates/tool_page.html` | Done |
| FAQ schema only when FAQ exists | `templates/tool_page.html` | Done |

**Still required from you (env / external):**
1. Create GA4 property → put Measurement ID in `GA4_MEASUREMENT_ID`
2. Create Google Search Console property for `voxcraft.site` → paste verification code into `GOOGLE_SITE_VERIFICATION`
3. Set `PLAUSIBLE_DOMAIN=voxcraft.site` (optional but recommended)
4. Submit sitemap in Search Console: `https://voxcraft.site/sitemap.xml`

---

## 3. Prioritized Keyword List (40 Keywords)

### Tier 1 — Highest priority (own these first)
These have clear commercial/intent + match your strongest differentiators (Urdu/Hindi + free + no signup).

| # | Keyword | Target Page | Priority | Notes / Competitors |
|---|---------|-------------|----------|---------------------|
| 1 | urdu text to speech | /urdu-text-to-speech | P0 | Fliki, Narakeet, HeyGen, Voicely, FreeReadText |
| 2 | hindi text to speech | /hindi-text-to-speech | P0 | Same set |
| 3 | free text to speech online | /free-text-to-speech + homepage | P0 | TTSMaker, NaturalReader, Edge |
| 4 | text to speech for youtube | /text-to-speech-for-youtube | P0 | High creator intent |
| 5 | remove background noise from audio | /tools/remove-background-noise | P0 | Adobe Podcast, Noise Reducer AI, SoundTools |
| 6 | extract audio from video online | /tools/extract-audio-from-video | P0 | High volume utility |
| 7 | convert audio format online | /tools/convert-audio-format | P0 | Classic utility |
| 8 | voice cloning online free | /voice-cloning | P0 | ElevenLabs, VoiceKeep |
| 9 | ai music generator free | /tools/ai-music-generator | P1 | Growing category |
| 10 | speech to text urdu / hindi | /tools/transcribe-audio-to-text | P0 | Unique angle |

### Tier 2 — Tool-specific ranking keywords (one primary per tool)

| Tool Slug | Primary Keyword | Secondary Keywords |
|-----------|-----------------|--------------------|
| transcribe-audio-to-text | urdu speech to text | hindi speech to text, free audio transcription |
| convert-audio-format | convert audio format online | mp3 to wav online, convert m4a to mp3 |
| merge-audio-files | merge audio files online | combine audio clips free |
| trim-cut-audio | trim audio online | cut audio online free, audio cutter |
| remove-background-noise | remove background noise from audio | free audio denoise, noise reducer online |
| voice-changer | voice changer online free | pitch shift online, robot voice changer |
| extract-audio-from-video | extract audio from video | mp4 to mp3 online free |
| ai-music-generator | ai music generator | text to music free |
| normalize-audio-volume | normalize audio volume online | audio loudness normalizer |
| adjust-audio-volume | adjust audio volume online | increase volume of audio online |
| change-audio-speed | change audio speed online | speed up audio online free |
| fade-audio | fade in fade out audio online | add fade to audio |
| split-audio-by-silence | split audio by silence | split recording by pauses |
| reverse-audio | reverse audio online | play audio backwards |
| stereo-to-mono | stereo to mono converter | convert stereo to mono online |
| loop-audio | loop audio online | repeat audio clip free |
| simple-audio-eq | online audio eq | bass treble boost online |
| video-audio-redub | video redub online | translate video audio, revoice video |

### Tier 3 — Supporting / long-tail (blog + SEO landings)

11. punjabi text to speech  
12. bengali text to speech  
13. tamil text to speech  
14. telugu text to speech  
15. how to create youtube voiceover  
16. audio tools for youtubers  
17. free ai voice generator  
18. multilingual text to speech  
19. roman urdu text to speech  
20. best free tts for youtube  
21. ai voiceover for faceless youtube  
22. online audio editor free  
23. denoise podcast audio free  
24. mp4 to mp3 converter free  
25. text to speech no signup  
26. neural text to speech online  
27. free voice cloning no credit card  
28. change pitch of voice online  
29. split long audio into clips  
30. fade audio for youtube  
31. normalize volume before youtube upload  
32. urdu ai voice generator  
33. hindi ai voice for youtube  
34. free background noise remover  
35. extract audio from youtube video (careful – copyright)  
36. combine multiple mp3 files  
37. online audio cutter no install  
38. text to speech commercial use free  
39. ai music from text prompt  
40. video translation voiceover  

---

## 4. Competitor Snapshot (2026)

| Competitor | Strength | Weakness you can attack |
|------------|----------|-------------------------|
| **ElevenLabs** | Best voice quality, cloning | Expensive, limited free, English-first |
| **TTSMaker** | Truly free export, many languages | Voice quality mediocre |
| **Adobe Podcast Enhance** | Excellent speech denoise | Account required, voice-only, limited |
| **Narakeet / Fliki / HeyGen** | Urdu voices exist | Paywalled, video-centric |
| **SoundTools / Noise Reducer AI** | Fast denoise | Single-purpose |
| **NaturalReader / Speechify** | Reading focus | Not creator/export oriented |

**Your edge:**  
Free + no signup + strong Urdu/Hindi/South-Asian focus + 18 practical tools in one place + commercial-friendly free tier.

---

## 5. Implementation Order (What to do next)

### Week 1 — Activate tracking & Search Console
1. Create GA4 property → set `GA4_MEASUREMENT_ID`
2. Search Console → verify with existing meta → submit sitemap
3. Set `PLAUSIBLE_DOMAIN=voxcraft.site`
4. Run PageSpeed Insights on homepage + 3 tool pages → note LCP/CLS

### Week 2 — On-page keyword polish
- Review each tool title/H1 against the primary keyword in the table above
- Use `/admin/seo` to tweak any weak titles without code deploys
- Add 1–2 extra FAQ questions per high-priority tool (helps both Google + AEO)

### Week 3 — Content velocity
- Publish 4–6 blog posts/month targeting Tier 3 keywords
- Link every blog post to the matching tool page + SEO landing page
- Add internal links from SEO landings → related tools

### Week 4+ — Authority & AEO/GEO
- Start quality backlink outreach (guest posts, tool directories, creator communities)
- Create “answer-ready” content blocks (clear definitions, step lists, comparison tables) so ChatGPT / Gemini / Perplexity can cite you
- Monitor rankings weekly (Google Search Console + free rank trackers)

---

## 6. AEO / GEO (Answer Engine Optimization) Checklist

Google is no longer the only search surface. To appear in ChatGPT, Gemini, Perplexity, etc.:

1. **Clear, self-contained answers** at the top of every page (first 40–60 words)
2. **HowTo + FAQ schema** (already added)
3. **Comparison tables** (“VoxCraft vs ElevenLabs free tier”)
4. **Entity consistency** — always use the same brand name + product names
5. **Original data** where possible (e.g. “we tested X Urdu voices…”)
6. **Fast, crawlable, no JS-only content**

---

## 7. Monitoring & Reporting (Automated)

Once GA4 + Search Console are live:

| Report | Tool | Cadence |
|--------|------|---------|
| Organic traffic & top queries | Search Console | Weekly |
| Page-level performance | GA4 | Weekly |
| Core Web Vitals | Search Console / PageSpeed | Monthly |
| Rank tracking (top 20 keywords) | Free: Search Console + Google Sheets or paid (Ahrefs/SEMrush) | Weekly |
| Backlink growth | Search Console Links report or Ahrefs | Monthly |

Simple free setup:
- Google Looker Studio dashboard connected to GA4 + Search Console
- One weekly email to yourself with top movers

---

## 8. Accessibility Quick Wins (already partially done)

- Semantic breadcrumb with `aria-label` and `aria-current`
- Proper `alt` on avatars
- Ensure every interactive control has a visible label (check tool widgets)
- Run axe or Lighthouse accessibility audit after next deploy

---

## 9. Next Concrete Actions for You

1. **Deploy the code changes** in this repo (GA4, schema, breadcrumb, alt fixes)
2. **Set the three env vars**: `GA4_MEASUREMENT_ID`, `GOOGLE_SITE_VERIFICATION`, `PLAUSIBLE_DOMAIN`
3. **Verify in Search Console** and submit sitemap
4. **Pick the top 5 keywords** from Tier 1 and double-check those pages’ titles/H1s in `/admin/seo`
5. **Schedule 4 blog posts** this month targeting Tier 3 keywords

After the above is live for 2–3 weeks we can re-audit rankings and decide whether the agency’s Off-Page package (backlinks) is worth the 40,000/month spend.

---

## 10. All Tool Titles Fully Optimized (2026-09-15)

Every tool now has a keyword-first title + H1 + meta that matches high-intent search patterns ("... online free", primary action keyword, brand).

| Tool | Primary Keyword Target |
|------|------------------------|
| transcribe-audio-to-text | urdu speech to text / hindi speech to text |
| convert-audio-format | convert audio format online |
| merge-audio-files | merge audio files online |
| trim-cut-audio | trim audio online / cut audio online |
| remove-background-noise | remove background noise from audio |
| voice-changer | voice changer online free |
| extract-audio-from-video | extract audio from video online |
| ai-music-generator | ai music generator free |
| normalize-audio-volume | normalize audio volume online |
| adjust-audio-volume | adjust audio volume online |
| change-audio-speed | change audio speed online |
| fade-audio | fade in fade out audio online |
| split-audio-by-silence | split audio by silence |
| reverse-audio | reverse audio online |
| stereo-to-mono | stereo to mono converter |
| loop-audio | loop audio online |
| simple-audio-eq | online audio eq / bass treble |
| video-audio-redub | video redub / ai video dubbing |

---

## 11. Competitor Research – Remaining Tools (2026)

### Utility Audio Tools (merge / trim / convert / fade / loop / EQ / reverse / mono)
**Main competitors:**
- audioeditor.org, audio-edit.com, audiokit.net, audiotrick.com, pi7.org, wutools.com, musictrim.com, aijinglemaker.com, timbrica.com

**Pattern they use:**
- Titles almost always contain “Online Free” or “Free Online”
- H1s are short action phrases
- Heavy emphasis on “no signup / no install / browser-based / private”

**Your advantage:** You already bundle these with TTS + voice cloning + music + redub. Most competitors are pure utility sites with no AI voice offering.

### Video Redub / AI Dubbing
**Main competitors:**
- Trupeer AI, VEED, Vivideo, Kapwing, Voxdub, videodubbing.com, Rewind.ai

**Pattern:**
- Heavy focus on “AI dubbing”, “lip-sync”, “120+ languages”
- Most are freemium with tight free limits
- Strong on video localization, weaker on pure audio toolkit + South-Asian languages

**Your edge:** 27 languages with strong Urdu/Hindi neural voices + free-tier audio tools in the same product.

---

## 12. AEO & GEO Optimization Techniques (2026 Playbook)

### Definitions
- **AEO (Answer Engine Optimization)** = getting cited/selected as the direct answer inside ChatGPT, Perplexity, Gemini, Claude, Grok, Google AI Overviews, voice assistants.
- **GEO (Generative Engine Optimization)** = broader discipline of being cited or recommended inside any generative AI summary.

### Highest-ROI Techniques (evidence-backed)

1. **Answer-first content**
   - First 40–60 words of every important section must fully answer the query.
   - Put the exact question people ask as an H2/H3, then answer immediately.

2. **FAQ + HowTo schema** (already implemented)
   - FAQPage schema has been measured to increase AI citations dramatically.
   - HowTo schema helps step-by-step queries.

3. **Statistics + named sources**
   - Adding specific numbers + third-party citations lifts visibility ~30–40% in research.
   - Example: “In our tests of 12 free denoisers, X reduced steady hiss by ~…”

4. **Entity consistency**
   - Always use the same brand name, product names, and “sameAs” links in Organization schema.
   - Claim Wikidata / Knowledge Panel when possible.

5. **Self-contained passages**
   - Engines prefer 130–170 word blocks that fully answer a question without needing the rest of the page.

6. **Lists, tables, comparison blocks**
   - “VoxCraft vs ElevenLabs free tier”, “Best free tools for Urdu TTS 2026” style content is highly citable.

7. **Freshness signals**
   - Update key pages with “Updated September 2026” and new data.

8. **llms.txt / technical access**
   - Ensure robots.txt allows AI crawlers (already does).
   - Consider an `/llms.txt` file describing your product for LLM crawlers.

### Practical AEO/GEO Actions for VoxCraft (Next 30 Days)

| Action | Where | Why |
|--------|-------|-----|
| Rewrite first paragraph of every tool page as a direct answer | tool_pages.py intros | Answer-first |
| Add 2–3 extra FAQ questions per high-priority tool | /admin/seo or code | FAQ schema + coverage |
| Publish 2 comparison posts | Blog | “Best free Urdu TTS 2026”, “VoxCraft vs TTSMaker” |
| Add one original statistic or test result | Blog + tool pages | Statistics addition |
| Keep Organization + SoftwareApplication schema current | landing.html | Entity graph |
| Monitor mentions in ChatGPT / Perplexity / Gemini | Manual weekly prompts | Measurement |

### Example Answer-First Rewrite Pattern

**Before:**
> “This tool uses spectral noise reduction to pull down steady…”

**After (AEO-ready):**
> “Remove background noise from audio online for free with VoxCraft. Upload a recording, set the strength slider, and download a cleaner version in seconds — no account required.”

Then expand with the how-it-works and details underneath.

---

## 13. Final Status

- All 18 tool titles, metas, and H1s are now keyword-optimized.
- BreadcrumbList + HowTo + FAQ schemas are live on tool and SEO pages.
- GA4 support is coded and ready.
- Full keyword list + competitor map + AEO/GEO playbook is documented.

**Next human steps remain the same:** deploy → set env vars → Search Console → start content velocity on Tier 1 & Tier 3 keywords.
