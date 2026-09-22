"""Content for VoxCraft's dedicated SEO landing pages.

These pages are informational entry points only. They reuse existing public
routes and tools, so adding or editing a page here cannot change audio, TTS,
payments, accounts, or usage-limit behaviour.
"""

import json
import os

SEO_PAGES = {
    "urdu-text-to-speech": {
        "title": "Urdu Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Create Urdu AI voiceovers from text online with VoxCraft. Choose a voice, adjust rate and pitch, and generate narration for videos and other projects.",
        "eyebrow": "Urdu AI Voice",
        "h1": "Create an Urdu voiceover from text",
        "intro": ['Create Urdu AI voiceovers from text online with VoxCraft Voice Studio. Choose an Urdu neural voice, paste your script, adjust rate or pitch if needed, and generate narration for YouTube, courses, or explainers — free tier available with no account required.', 'Urdu text-to-speech is not just “another language slot.” Pronunciation of names, numbers, and mixed English–Urdu lines is where generic global TTS often fails listeners. VoxCraft treats Urdu as a first-class workflow: test short samples, revise spellings, then generate longer sections.', 'A practical creator path: draft the script → generate 20–40 seconds → listen on phone speakers → fix hard words → generate the rest → optionally clean or convert the file with free <a href="/tools">audio tools</a>. For YouTube-specific structure, see <a href="/text-to-speech-for-youtube">text to speech for YouTube</a> and <a href="/how-to-create-youtube-voiceover">how to create a YouTube voiceover</a>.', 'Commercial use of audio you generate is allowed under current Terms, subject to those terms and any rights in material you upload. Always verify live pricing limits on the pricing page before committing a high-volume channel.'],
        "steps": ['Open Voice Studio and select Urdu from the language list.', 'Preview two or three voices on the same short line from your real script.', 'Paste a short section first (opening paragraph), generate, and listen for names and numbers.', 'Revise spellings or punctuation where needed, then generate remaining sections.', 'Download and, if required, trim, merge, or convert with VoxCraft audio tools before editing video.'],
        "use_cases": [('YouTube narration', 'Faceless and explainer channels that need steady Urdu voiceover without daily studio time.'), ('Learning content', 'Turn written Urdu lessons or notes into audio for listening practice.'), ('Creator drafts', 'Hear a script before hiring talent or recording yourself.'), ('Localization', 'Produce Urdu versions of English outlines when you already have the written translation.')],
        "faq": [('Is Urdu text to speech free on VoxCraft?', 'Yes. You can try Urdu voices on the free tier without creating an account, within published usage limits. See pricing for Pro limits.'), ('Which Urdu voice should I pick?', 'Preview with a line from your actual niche (news, education, story). The “best” voice depends on audience age and formality.'), ('Can I mix English words in an Urdu script?', 'Yes, but mixed lines need testing. Generate a short sample that includes the English terms you care about.'), ('Nastaliq vs Roman Urdu — what should I type?', 'Native script usually produces more reliable pronunciation than pure Roman Urdu. If you only have Roman, test carefully.'), ('Can I use the audio on monetized YouTube?', 'Audio you generate is yours to use commercially under current Terms — confirm the Terms page for details.'), ('How do I avoid robotic delivery?', 'Use natural punctuation, shorter sentences, and section-by-section generation instead of one giant block.'), ('Where do I go after generating audio?', 'Common next steps: trim, merge, denoise, or convert format in the free toolset, then drop into your editor.'), ('How is this different from global TTS sites?', 'Many tools add Urdu late. VoxCraft prioritizes South Asian creator workflows alongside English, with tools around the voiceover, not only a single generate button.')],
        "cta_label": "Try Urdu voices in Voice Studio",
        "related_links": [('Open Voice Studio', '/studio'), ('Free text to speech', '/free-text-to-speech'), ('Text to speech for YouTube', '/text-to-speech-for-youtube'), ('Hindi text to speech', '/hindi-text-to-speech'), ('Remove background noise', '/tools/remove-background-noise'), ('Convert audio format', '/tools/convert-audio-format')],
    },
    "hindi-text-to-speech": {
        "title": "Hindi Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Create Hindi AI voiceovers from text online with VoxCraft. Select a Hindi voice, adjust delivery, and generate narration for videos and other projects.",
        "eyebrow": "Hindi AI Voice", "h1": "Create a Hindi voiceover from text",
        "intro": ['Create Hindi AI voiceovers from text online with VoxCraft. Select a Hindi neural voice, enter Devanagari script where possible, and generate narration for videos, courses, and explainers — free tier available without required signup.', 'Hindi TTS quality shows up on names, numbers, and English loanwords inside Hindi sentences. Always test a short real sample before generating a full episode-length script.', 'Pair generation with creator tools when needed: <a href="/tools/trim-cut-audio">trim</a>, <a href="/tools/merge-audio-files">merge</a>, <a href="/tools/normalize-audio-volume">normalize loudness</a>, or <a href="/tools/remove-background-noise">denoise</a> if you recorded something alongside AI narration.', 'For bilingual channels, keep Urdu and Hindi tests separate rather than assuming one voice setting fits both audiences. See also <a href="/urdu-text-to-speech">Urdu text to speech</a> and <a href="/text-to-speech-for-youtube">TTS for YouTube</a>.'],
        "steps": ['Open Voice Studio and choose Hindi.', 'Preview voices on a line that includes a name and a number.', 'Generate a short opening section first.', 'Adjust rate/pitch if available, then produce remaining sections.', 'Export and assemble in your video editor.'],
        "use_cases": [('YouTube explainers', 'Hindi narration for educational and product videos.'), ('Courses', 'Audio versions of written lessons.'), ('Drafting', 'Hear pacing before a live record session.')],
        "faq": [('Is Hindi TTS free?', 'Yes within free-tier limits, no account required to start.'), ('Should I use Devanagari?', 'Yes when you can — native script usually improves pronunciation versus pure Roman Hindi.'), ('Commercial use?', 'Allowed under current Terms for audio you generate; check Terms for full rules.'), ('Can I combine with voice cloning?', 'Voice cloning is a separate Pro+ workflow. Stock Hindi neural voices are available in Studio on free/Pro tiers as published.'), ('How long should test samples be?', '20–40 seconds of real script beats a single marketing demo line.'), ('What if numbers sound wrong?', 'Rewrite numbers as words or restructure the sentence and regenerate that clause only.'), ('Where is the full voice list?', 'Inside Voice Studio’s language and voice selectors — the live list is authoritative.')],
        "cta_label": "Try Hindi voices in Voice Studio",
        "related_links": [('Voice Studio', '/studio'), ('Urdu text to speech', '/urdu-text-to-speech'), ('Free TTS', '/free-text-to-speech'), ('YouTube voiceover guide', '/how-to-create-youtube-voiceover'), ('Normalize volume', '/tools/normalize-audio-volume')],
    },
    "punjabi-text-to-speech": {
        "title": "Punjabi Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Free Punjabi text to speech online. Generate Punjabi (Gurmukhi) AI voiceovers for YouTube, explainers, and learning — neural voices, no signup required to start.",
        "eyebrow": "Punjabi AI Voice",
        "h1": "Create a Punjabi voiceover from text",
        "intro": [
            "Punjabi text-to-speech on VoxCraft is built for creators who publish for Punjabi-speaking audiences in India, Pakistan, and the diaspora — not as a buried language option. Paste Gurmukhi (or carefully tested Roman Punjabi), pick a neural voice, and download narration for Shorts, long-form explainers, or course audio.",
            "What usually breaks Punjabi TTS: mixed English product names, village and family names, and numbers written only as digits. Always generate a 20–40 second sample that includes those hard bits before you commit a full episode.",
            "Gurmukhi script generally reads more reliably than pure Romanized Punjabi. If your draft is in Roman, convert key lines to Gurmukhi where you can, or test both. After export, use free <a href=\"/tools\">audio tools</a> to <a href=\"/tools/trim-cut-audio\">trim</a>, <a href=\"/tools/merge-audio-files\">merge</a>, or <a href=\"/tools/normalize-audio-volume\">normalize</a>.",
            "Related workflows: <a href=\"/hindi-text-to-speech\">Hindi TTS</a>, <a href=\"/urdu-text-to-speech\">Urdu TTS</a>, and <a href=\"/text-to-speech-for-youtube\">TTS for YouTube</a>.",
        ],
        "steps": [
            "Open Voice Studio and select Punjabi from the language list.",
            "Preview two voices on the same short line from your real script (include one name and one number).",
            "Generate only the opening 20–40 seconds; listen on phone speakers.",
            "Fix spellings or rewrite awkward English loanwords, then generate remaining sections.",
            "Download and trim/merge/normalize before dropping into your video editor.",
        ],
        "use_cases": [
            ("Punjabi YouTube & Shorts", "Faceless explainers, news recaps, and product reviews aimed at Punjabi viewers."),
            ("Diaspora content", "Community updates and tutorials for audiences in the UK, Canada, and the Gulf."),
            ("Learning & scripture drafts", "Hear written Punjabi lessons or notes before a human record session."),
            ("Bilingual channels", "Ship a Punjabi track alongside Hindi or English versions of the same outline."),
        ],
        "faq": [
            ("Is Punjabi text to speech free on VoxCraft?", "Yes within free-tier limits, with no account required to start. See pricing for Pro quotas."),
            ("Gurmukhi or Roman Punjabi?", "Gurmukhi usually produces clearer pronunciation. Roman can work for short tests but needs careful listening."),
            ("Can I mix English words in a Punjabi script?", "Yes — test lines that include brand names and tech terms; rewrite if a word is stressed oddly."),
            ("Commercial use on YouTube?", "Generated audio is usable commercially under current Terms; confirm the live Terms page."),
            ("How do I avoid flat delivery?", "Shorter sentences, natural punctuation, and section-by-section generation beat one giant block."),
            ("Where is the live voice list?", "Inside Voice Studio’s language and voice selectors — the catalog is the source of truth."),
        ],
        "cta_label": "Try Punjabi voices in Voice Studio",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("Hindi text to speech", "/hindi-text-to-speech"),
            ("Urdu text to speech", "/urdu-text-to-speech"),
            ("Free text to speech", "/free-text-to-speech"),
            ("Normalize volume", "/tools/normalize-audio-volume"),
        ],
    },
    "bengali-text-to-speech": {
        "title": "Bengali Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Free Bengali (Bangla) text to speech online. Generate Bengali AI voiceovers for YouTube, courses, and explainers — neural voices, download MP3, no signup to start.",
        "eyebrow": "Bengali AI Voice",
        "h1": "Create a Bengali voiceover from text",
        "intro": [
            "Bengali (Bangla) text-to-speech on VoxCraft targets creators in West Bengal, Bangladesh, and Bangla-speaking diaspora channels. Use native Bengali script when you can, preview a neural voice on a real line from your niche, then generate section by section.",
            "Bangla TTS quality shows up on conjunct characters, English loanwords inside Bengali sentences, and place names. A short sample with those cases saves more time than regenerating a full video later.",
            "After generation, creators often <a href=\"/tools/trim-cut-audio\">trim</a> intros, <a href=\"/tools/merge-audio-files\">merge</a> scenes, or <a href=\"/tools/normalize-audio-volume\">normalize loudness</a> for YouTube. See also <a href=\"/hindi-text-to-speech\">Hindi TTS</a> and <a href=\"/text-to-speech-for-youtube\">TTS for YouTube</a>.",
        ],
        "steps": [
            "Open Voice Studio and choose Bengali.",
            "Preview voices on a line that includes a name and a number.",
            "Generate a short opening section first and listen on phone speakers.",
            "Revise spellings or punctuation, then produce the remaining sections.",
            "Export and assemble in your video editor.",
        ],
        "use_cases": [
            ("Bangla YouTube", "Educational explainers, tech reviews, and faceless channels."),
            ("Online courses", "Turn written Bengali lessons into listen-along audio."),
            ("News-style recaps", "Steady narration for daily or weekly summary videos."),
            ("Localization", "Bengali versions of an English or Hindi outline you already wrote."),
        ],
        "faq": [
            ("Is Bengali TTS free?", "Yes within free-tier limits; no account required to start."),
            ("Should I type in Bengali script?", "Yes when possible — native script usually improves pronunciation versus pure Roman Bangla."),
            ("English words inside Bengali?", "Common and supported; always test brand names and technical terms in a short sample."),
            ("Commercial use?", "Allowed for audio you generate under current Terms — read the live Terms page."),
            ("How long should test samples be?", "20–40 seconds of real script beats a single marketing demo line."),
            ("Next tools after TTS?", "Trim, merge, denoise, or convert format in the free toolset, then edit video."),
        ],
        "cta_label": "Try Bengali voices in Voice Studio",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("Hindi text to speech", "/hindi-text-to-speech"),
            ("Free text to speech", "/free-text-to-speech"),
            ("Text to speech for YouTube", "/text-to-speech-for-youtube"),
            ("Merge audio files", "/tools/merge-audio-files"),
        ],
    },
    "tamil-text-to-speech": {
        "title": "Tamil Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Free Tamil text to speech online. Generate Tamil AI voiceovers for YouTube, education, and product videos — neural voices, downloadable audio, no signup to start.",
        "eyebrow": "Tamil AI Voice",
        "h1": "Create a Tamil voiceover from text",
        "intro": [
            "Tamil text-to-speech on VoxCraft is aimed at creators shipping for Tamil Nadu, Sri Lankan Tamil audiences, and global Tamil YouTube. Paste Tamil script, choose a neural voice, and export narration without installing a desktop TTS app.",
            "Tamil has a rich written tradition and precise phonology — TTS mistakes often appear on classical or formal vocabulary, English tech terms, and long compound words. Test those cases early.",
            "Practical path: draft → short sample → fix → full generate → <a href=\"/tools/trim-cut-audio\">trim</a> / <a href=\"/tools/normalize-audio-volume\">normalize</a>. Pair with <a href=\"/telugu-text-to-speech\">Telugu TTS</a> if you run a multi-South-Indian channel.",
        ],
        "steps": [
            "Open Voice Studio and select Tamil.",
            "Preview two voices on a line from your actual niche (not a generic hello).",
            "Generate 20–40 seconds; check names, places, and English product words.",
            "Adjust the script, then generate remaining sections labeled by scene.",
            "Download and prepare the file for your editor.",
        ],
        "use_cases": [
            ("Tamil YouTube explainers", "Tech, finance, and education channels that need steady narration."),
            ("Course audio", "Lesson scripts turned into listen-on-commute tracks."),
            ("Product demos", "Consistent product voice without daily studio time."),
            ("Multilingual South India", "Tamil track alongside Telugu or English versions."),
        ],
        "faq": [
            ("Is Tamil text to speech free?", "Yes within published free-tier limits, no account required to start."),
            ("Tamil script or Roman?", "Native Tamil script is strongly preferred for accuracy."),
            ("Can I use this on monetized YouTube?", "Generated audio is commercially usable under current Terms — verify the Terms page."),
            ("Why does one word sound wrong?", "Rewrite the word, add punctuation, or split a long sentence, then regenerate only that section."),
            ("Voice cloning for Tamil?", "Stock Tamil neural voices are in Studio; cloning is a separate Pro+ workflow when available for your plan."),
            ("Where do I see all Tamil voices?", "Voice Studio language selector — live list is authoritative."),
        ],
        "cta_label": "Try Tamil voices in Voice Studio",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("Telugu text to speech", "/telugu-text-to-speech"),
            ("Free text to speech", "/free-text-to-speech"),
            ("How to create a YouTube voiceover", "/how-to-create-youtube-voiceover"),
            ("Normalize volume", "/tools/normalize-audio-volume"),
        ],
    },
    "telugu-text-to-speech": {
        "title": "Telugu Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Free Telugu text to speech online. Generate Telugu AI voiceovers for YouTube, courses, and regional content — neural voices, MP3 download, no signup required to start.",
        "eyebrow": "Telugu AI Voice",
        "h1": "Create a Telugu voiceover from text",
        "intro": [
            "Telugu text-to-speech on VoxCraft serves creators in Andhra Pradesh, Telangana, and Telugu diaspora channels. Generate neural narration from written Telugu, preview delivery, and download files ready for CapCut, Premiere, or an LMS.",
            "Watch for English brand names, numeric prices, and formal vs colloquial tone. A sample that includes a price line and a product name is more useful than a poetic demo sentence.",
            "After TTS: <a href=\"/tools/trim-cut-audio\">trim</a>, <a href=\"/tools/merge-audio-files\">merge</a>, or <a href=\"/tools/remove-background-noise\">denoise</a> if you mixed in a live recording. See also <a href=\"/tamil-text-to-speech\">Tamil TTS</a> and <a href=\"/kannada-text-to-speech\">Kannada TTS</a>.",
        ],
        "steps": [
            "Open Voice Studio and choose Telugu.",
            "Preview voices on a real script line with a name and a number.",
            "Generate a short section first; listen on phone speakers.",
            "Fix problem words, then generate the rest by section.",
            "Export and align to your video timeline.",
        ],
        "use_cases": [
            ("Telugu YouTube", "Explainers, reviews, and faceless educational channels."),
            ("EdTech", "Course modules and revision audio in Telugu."),
            ("Regional marketing", "Product explainers for Telugu-speaking customers."),
            ("Multi-language publish", "Same outline in Telugu, Tamil, and English."),
        ],
        "faq": [
            ("Is Telugu TTS free on VoxCraft?", "Yes within free-tier limits; no signup required to start."),
            ("Native Telugu script?", "Yes — prefer Telugu script over pure Roman for clearer results."),
            ("Commercial rights?", "Audio you generate is usable under current Terms; check the live Terms page."),
            ("Numbers sound wrong?", "Write numbers as words for critical lines, or restructure the sentence and regenerate that clause."),
            ("How is this different from global TTS sites?", "VoxCraft prioritizes South Asian creator workflows and free tools around the file, not only a generate button."),
            ("What if I need higher volume?", "Upgrade when free caps block your schedule — see pricing."),
        ],
        "cta_label": "Try Telugu voices in Voice Studio",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("Tamil text to speech", "/tamil-text-to-speech"),
            ("Kannada text to speech", "/kannada-text-to-speech"),
            ("Free text to speech", "/free-text-to-speech"),
            ("Text to speech for YouTube", "/text-to-speech-for-youtube"),
        ],
    },
    "text-to-speech-for-youtube": {
        "title": "Text to Speech for YouTube — AI Voiceover | VoxCraft",
        "meta_description": "Learn a practical text-to-speech workflow for YouTube videos: prepare a script, test voices, review pronunciation, and create narration with VoxCraft.",
        "eyebrow": "YouTube Voiceover", "h1": "Use text to speech for YouTube narration",
        "intro": ['Use text to speech for YouTube narration with a workflow built for creators: write for the ear, test a short opening, generate in sections, then edit. VoxCraft Voice Studio supports multilingual neural voices including Urdu and Hindi, with a free tier that does not require signup.', 'TTS fails on YouTube when people generate a 10-minute monologue in one click and skip listening. Treat AI voice like a voice actor take: short tests, revisions, then full generate.', 'After audio is ready, creators often <a href="/tools/normalize-audio-volume">normalize loudness</a>, <a href="/tools/trim-cut-audio">trim</a>, or <a href="/tools/merge-audio-files">merge</a> intros and outros. For language-specific landing pages see <a href="/urdu-text-to-speech">Urdu</a> and <a href="/hindi-text-to-speech">Hindi</a>.', 'Faceless channels, explainers, and product reviews are the common fits. Documentary-style emotional performance may still need human VO — TTS is a production tool, not a guarantee of cinematic acting.'],
        "steps": ['Finish and proofread the script for spoken delivery.', 'Generate only the first 20–40 seconds and listen on phone speakers.', 'Fix names, numbers, and awkward phrases.', 'Generate remaining sections; keep files labeled by scene.', 'Trim/merge/normalize as needed, then align to the timeline.'],
        "use_cases": [('Faceless YouTube', 'Consistent narration without daily recording.'), ('Explainers', 'Steady educational delivery.'), ('Multilingual channels', 'Urdu/Hindi/English variants of the same outline.')],
        "faq": [('Is TTS allowed on monetized YouTube?', 'YouTube allows AI-assisted content under its policies when you follow their rules; also follow VoxCraft Terms. Policies evolve — verify on YouTube Help.'), ('Should I generate the whole video at once?', 'Section-by-section is safer for quality control and easier retakes.'), ('What loudness should I aim for?', 'Many creators normalize toward platform expectations; use the <a href="/tools/normalize-audio-volume">normalize tool</a> and check on multiple devices.'), ('Urdu or Hindi for my audience?', 'Match the audience language; test both if your channel is bilingual.'), ('Free tier enough for weekly uploads?', 'Depends on length and frequency. Watch in-product limits; upgrade when caps block your schedule.'), ('How do I make TTS less obvious?', 'Natural punctuation, moderate speed, and human editing of the script matter more than any single “emotion” toggle.'), ('Can I combine TTS with my real voice?', 'Yes — common hybrid: AI for drafts or secondary languages, human for flagship episodes.')],
        "cta_label": "Create a YouTube voiceover",
        "related_links": [('Voice Studio', '/studio'), ('How to create a YouTube voiceover', '/how-to-create-youtube-voiceover'), ('Audio tools for YouTubers', '/audio-tools-for-youtubers'), ('Normalize volume', '/tools/normalize-audio-volume'), ('Merge audio', '/tools/merge-audio-files')],
    },
    "free-text-to-speech": {
        "title": "Free Text to Speech Online — AI Voices | VoxCraft",
        "meta_description": "Try VoxCraft's free text-to-speech workflow online. Choose an available voice, enter text, and generate narration within the current free-tier limits.",
        "eyebrow": "Free TTS", "h1": "Try text to speech online for free",
        "intro": ['Try free text to speech online with VoxCraft — no account required on the free tier. Choose a language and neural voice, paste text, generate narration, and download within published limits.', '“Free TTS” tools differ on three things that matter: voice quality, language coverage, and whether commercial use is allowed. VoxCraft is built for creators who need usable multilingual narration (including Urdu and Hindi) plus free utilities around the file.', 'Use free generation to test scripts and ship small projects. Move to Pro when daily limits block your publishing schedule. See <a href="/pricing">pricing</a> for current numbers rather than screenshots from older posts.', 'Next reads: <a href="/urdu-text-to-speech">Urdu TTS</a>, <a href="/hindi-text-to-speech">Hindi TTS</a>, <a href="/text-to-speech-for-youtube">TTS for YouTube</a>, and the <a href="/tools">audio tools directory</a>.'],
        "steps": ['Open Voice Studio without creating an account.', 'Pick language and voice; preview a sample.', 'Paste a short test script and generate.', 'Download and review on phone speakers.', 'Check pricing if you need higher limits or Pro+ features like cloning.'],
        "use_cases": [('Quick tests', 'Compare voices on the same paragraph.'), ('Small projects', 'Ship short videos within free limits.'), ('Education', 'Teachers and students testing narration ideas.')],
        "faq": [('Do I need a credit card for free TTS?', 'No. Free tier does not require signup or a card to start.'), ('Is free audio commercial-friendly?', 'Generated audio is usable commercially under current Terms — always read the live Terms page.'), ('What are the free limits?', 'Limits can change. The Studio UI and pricing page show current daily/monthly allowances.'), ('Free vs Pro — when to upgrade?', 'Upgrade when you hit caps, need batch volume, or want Pro+ features such as voice cloning.'), ('Which languages are free?', 'Free tier includes access to the Studio voice library subject to usage caps; Urdu and Hindi are first-class options.'), ('Can I remove watermarks?', 'VoxCraft does not market TTS downloads as watermarked promo files; you get the generated audio file under the plan rules.'), ('How does this compare to TTSMaker or browser read-aloud?', 'Browser read-aloud is for listening, not always for exportable creator workflows. VoxCraft focuses on downloadable narration plus editing tools.')],
        "cta_label": "Try text to speech",
        "related_links": [('Voice Studio', '/studio'), ('Urdu TTS', '/urdu-text-to-speech'), ('Hindi TTS', '/hindi-text-to-speech'), ('YouTube TTS workflow', '/text-to-speech-for-youtube'), ('All tools', '/tools')],
    },
    "how-to-create-youtube-voiceover": {
        "title": "How to Create a YouTube Voiceover | VoxCraft",
        "meta_description": "Learn a practical YouTube voiceover workflow from script preparation and voice testing to audio review, editing and final export.",
        "eyebrow": "Creator Guide", "h1": "How to create a YouTube voiceover",
        "intro": ["A reliable voiceover workflow starts before you open a voice tool. A clean script, short test, and deliberate review process can prevent repeated fixes later in editing.", "The exact workflow works whether you use an AI voice or record your own voice: prepare, test, review, edit, then match the final audio to the video."],
        "steps": ["Write for the ear, using short and natural sentences.", "Test the first 20–40 seconds before producing the full narration.", "Correct names, numbers, pacing and difficult phrases.", "Generate or record the final sections, then trim and merge them as needed.", "Listen once with the finished video before export."],
        "use_cases": [("New creators", "Create a repeatable process instead of improvising each video."), ("Faceless videos", "Keep narration production separate from the visual edit."), ("Team workflows", "Use the script as the source of truth for revisions and replacements.")],
        "faq": [("What should I test first?", "Test the opening and any line containing names, dates, numbers or unusual words."), ("Why split narration into sections?", "Small sections are easier to replace without regenerating or re-recording an entire project."), ("What comes after narration?", "Review the final timing against the video, then make any small edits before export.")],
        "cta_label": "Open Voice Studio",
    },
    "audio-tools-for-youtubers": {
        "title": "Audio Tools for YouTubers — Online Toolkit | VoxCraft",
        "meta_description": "Explore practical online audio tools for YouTubers, including transcription, trimming, merging, format conversion, noise reduction and video-to-audio extraction.",
        "eyebrow": "Creator Toolkit", "h1": "Practical audio tools for YouTube creators",
        "intro": ["Most YouTube projects do not need a complex audio suite for every task. Small jobs such as trimming a clip, joining narration sections or converting a file can often be handled with focused tools.", "VoxCraft groups common creator tasks in one toolkit so you can move between voice creation and basic audio processing without changing your overall workflow."],
        "steps": ["Start with the task you actually need: transcribe, trim, merge, convert, clean or extract.", "Keep the original file before making destructive edits.", "Use one tool at a time and review the result before the next step.", "Export a compatible format for your video editor or publishing workflow."],
        "use_cases": [("Narration cleanup", "Trim and combine sections before placing them in the video timeline."), ("Repurposing", "Transcribe spoken content into text for notes or written material."), ("Format compatibility", "Convert audio when an editor or platform requires a different file type.")],
        "faq": [("Which tool should I use first?", "Start with the problem you need to solve rather than processing every file through every tool."), ("Should I keep the original?", "Yes. Keep an untouched original whenever you may need to redo an edit later."), ("Are all tools the same?", "Each tool is focused on a specific task. Check its dedicated page for supported formats and current limits.")],
        "cta_label": "Explore VoxCraft audio tools",
        "related_links": [
            ("Transcribe audio to text", "/tools/transcribe-audio-to-text"),
            ("Trim or cut audio", "/tools/trim-cut-audio"),
            ("Merge audio files", "/tools/merge-audio-files"),
            ("Convert audio format", "/tools/convert-audio-format"),
            ("Remove background noise", "/tools/remove-background-noise"),
            ("Extract audio from video", "/tools/extract-audio-from-video"),
        ],
    },
    # --- High-intent keyword pages (2026 research) ---
    "ai-video-dubbing": {
        "title": "AI Video Dubbing Online — Translate Video | VoxCraft",
        "meta_description": "Dub videos online with AI: transcribe, translate, and re-voice clips in English, Hindi, Urdu and more. Timed segments, free tier to start — no desktop install.",
        "eyebrow": "Video Redub",
        "h1": "AI video dubbing online",
        "intro": [
            "AI video dubbing lets you take a spoken clip, translate it, and replace the voice track without rebuilding the whole edit. VoxCraft Video Redub runs that pipeline in the browser: speech recognition, translation, neural TTS, then timed placement against the original video.",
            "Creators use this for short comedy clips, explainers, product demos, and regional YouTube versions. Results depend on source audio clarity and language pair — always preview before publishing.",
            "Start from <a href=\"/video-redub\">Video Redub</a> or the dedicated tool page <a href=\"/tools/video-audio-redub\">video audio redub</a>. Pair with <a href=\"/tools/extract-audio-from-video\">extract audio</a> or <a href=\"/tools/remove-background-noise\">denoise</a> when the source is noisy.",
        ],
        "steps": [
            "Upload a short video with clear speech (under the current size limit).",
            "Choose source language (e.g. Hindi) and target voice language.",
            "Run redub — Whisper or Google handles speech windows; translation and TTS follow.",
            "Preview the dubbed MP4, download video or audio-only, then publish or re-edit.",
        ],
        "use_cases": [
            ("Regional YouTube", "Ship Hindi or Urdu versions of an English explainer without re-recording."),
            ("Comedy & memes", "Quick English redubs of viral regional clips."),
            ("Course localization", "Draft localized narration before hiring talent."),
        ],
        "faq": [
            ("Is AI video dubbing free on VoxCraft?", "A free tier is available within published limits. Check pricing for Pro quotas."),
            ("Does it lip-sync?", "Phase 1 prioritizes timed audio windows. Faces are not re-animated."),
            ("Which languages work best?", "Clear Hindi/Urdu/English speech works best; noisy multi-speaker audio is harder."),
            ("How is this different from ElevenLabs Dubbing?", "VoxCraft targets short creator clips with a free path and South Asian language focus rather than enterprise localization suites."),
        ],
        "cta_label": "Open Video Redub",
        "related_links": [
            ("Video Redub", "/video-redub"),
            ("Video audio redub tool", "/tools/video-audio-redub"),
            ("Voice Studio", "/studio"),
            ("Voice cloning", "/voice-cloning"),
            ("Extract audio from video", "/tools/extract-audio-from-video"),
        ],
    },
    "ai-voice-generator": {
        "title": "AI Voice Generator Online — Neural Voices | VoxCraft",
        "meta_description": "Free AI voice generator for creators. Neural text-to-speech in Urdu, Hindi, English and 40+ languages. Download MP3 — no signup required to start.",
        "eyebrow": "AI Voice",
        "h1": "AI voice generator online",
        "intro": [
            "An AI voice generator turns written scripts into spoken audio. VoxCraft Voice Studio offers neural voices across major creator languages — including strong Urdu and Hindi coverage — with rate/pitch controls and downloadable files.",
            "Unlike browser read-aloud, this workflow is built for export: generate, preview on phone speakers, revise hard words, then download for YouTube, courses, or ads.",
            "Explore language pages: <a href=\"/urdu-text-to-speech\">Urdu</a>, <a href=\"/hindi-text-to-speech\">Hindi</a>, <a href=\"/free-text-to-speech\">free TTS</a>, or open the full <a href=\"/voices\">voice library</a>.",
        ],
        "steps": [
            "Open Voice Studio and pick a language.",
            "Preview two or three voices on a line from your real script.",
            "Generate a short section first; fix names and numbers.",
            "Generate the rest, download, then trim or normalize if needed.",
        ],
        "use_cases": [
            ("YouTube narration", "Faceless and explainer channels."),
            ("Product demos", "Consistent product voice without daily recording."),
            ("Multilingual drafts", "Hear a translation before a human VO session."),
        ],
        "faq": [
            ("Is the AI voice generator free?", "Yes within free-tier limits, no account required to start."),
            ("Can I use audio commercially?", "Generated audio is usable under current Terms — read the live Terms page."),
            ("Voice cloning vs stock voices?", "Stock neural voices are in Studio; cloning is a separate Pro+ workflow."),
        ],
        "cta_label": "Generate a voice",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("All voices", "/voices"),
            ("Free text to speech", "/free-text-to-speech"),
            ("Voice cloning", "/voice-cloning"),
        ],
    },
    "free-voice-cloning": {
        "title": "Free Voice Cloning Online — Clone a Sample | VoxCraft",
        "meta_description": "Learn how voice cloning works on VoxCraft. Clone a short sample for consistent narration. Free tier covers Studio voices; cloning is available on Pro+ plans.",
        "eyebrow": "Voice Cloning",
        "h1": "Voice cloning online",
        "intro": [
            "Voice cloning creates a reusable model from a short clean sample so you can generate new lines in a consistent voice. VoxCraft exposes cloning as a Pro+ workflow with consent checks — stock neural voices remain available on free and Pro tiers.",
            "Best results come from quiet, single-speaker audio (ideally 30+ seconds of varied speech). Avoid music beds and heavy compression.",
            "Start at <a href=\"/voice-cloning\">Voice Cloning</a>. For stock voices without cloning, use <a href=\"/studio\">Voice Studio</a>.",
        ],
        "steps": [
            "Prepare a clean sample (one speaker, little background noise).",
            "Open Voice Cloning and complete any consent steps shown.",
            "Upload the sample and create the clone when your plan allows.",
            "Generate test lines, then use the clone for longer scripts.",
        ],
        "use_cases": [
            ("Brand consistency", "Same host voice across a series."),
            ("Multilingual reuse", "Clone once, generate translated scripts where supported."),
            ("Draft vs final", "Clone for drafts; human record for flagship episodes."),
        ],
        "faq": [
            ("Is voice cloning free?", "Studio neural voices are free-tier friendly. Cloning requires an eligible Pro+ plan — see pricing."),
            ("Is cloning ethical?", "Only clone voices you own or have explicit permission to use. VoxCraft includes consent checks."),
            ("How long should the sample be?", "Clean 30–90 seconds of varied speech beats a noisy 10-second clip."),
        ],
        "cta_label": "Open Voice Cloning",
        "related_links": [
            ("Voice Cloning", "/voice-cloning"),
            ("Voice Studio", "/studio"),
            ("Pricing", "/pricing"),
            ("AI voice generator", "/ai-voice-generator"),
        ],
    },
    "marathi-text-to-speech": {
        "title": "Marathi Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Free Marathi text to speech online. Generate Marathi AI voiceovers in Devanagari for YouTube, education, and product videos — neural voices, no signup to start.",
        "eyebrow": "Marathi AI Voice",
        "h1": "Create a Marathi voiceover from text",
        "intro": [
            "Marathi text-to-speech on VoxCraft is for creators publishing to Maharashtra and Marathi-speaking audiences worldwide. Paste Devanagari Marathi, pick a neural voice, and download narration for explainers, Shorts, or course modules.",
            "Marathi shares Devanagari with Hindi but has its own vocabulary and rhythm. Do not assume a Hindi-optimized script will sound natural in Marathi — test names, city references, and formal vs conversational tone on a short sample.",
            "Workflow: short test → fix hard words → section generate → <a href=\"/tools/trim-cut-audio\">trim</a> / <a href=\"/tools/normalize-audio-volume\">normalize</a>. Related: <a href=\"/hindi-text-to-speech\">Hindi TTS</a>, <a href=\"/gujarati-text-to-speech\">Gujarati TTS</a>.",
        ],
        "steps": [
            "Open Voice Studio and select Marathi when listed.",
            "Preview voices on a real line that includes a name and a number.",
            "Generate 20–40 seconds and listen on phone speakers.",
            "Revise spellings or rewrite awkward loanwords, then generate remaining sections.",
            "Download and prepare the file for your editor.",
        ],
        "use_cases": [
            ("Marathi YouTube", "Educational and product channels targeting Maharashtra viewers."),
            ("Local business explainers", "Service and product narration without daily studio time."),
            ("Education", "Audio versions of written Marathi lessons and notes."),
            ("Bilingual publish", "Marathi track next to Hindi or English versions of the same outline."),
        ],
        "faq": [
            ("Is Marathi text to speech free?", "Yes within free-tier limits; no account required to start."),
            ("Devanagari or Roman Marathi?", "Devanagari is preferred for clearer pronunciation."),
            ("How is Marathi different from Hindi TTS?", "Different vocabulary and delivery norms — always preview Marathi on Marathi script, not a Hindi script re-labeled."),
            ("Commercial use?", "Generated audio is usable under current Terms; confirm the live Terms page."),
            ("Where is the live voice list?", "Voice Studio language selector."),
            ("What if Marathi is not listed?", "Catalog can expand; check Studio, or use related languages only when appropriate for your audience."),
        ],
        "cta_label": "Try Marathi voices in Voice Studio",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("Hindi text to speech", "/hindi-text-to-speech"),
            ("Gujarati text to speech", "/gujarati-text-to-speech"),
            ("Free text to speech", "/free-text-to-speech"),
            ("Normalize volume", "/tools/normalize-audio-volume"),
        ],
    },
    "gujarati-text-to-speech": {
        "title": "Gujarati Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Free Gujarati text to speech online. Generate Gujarati AI voiceovers for YouTube, business explainers, and learning — neural voices, downloadable audio, no signup to start.",
        "eyebrow": "Gujarati AI Voice",
        "h1": "Create a Gujarati voiceover from text",
        "intro": [
            "Gujarati text-to-speech on VoxCraft supports creators and small businesses who need clear Gujarati narration for YouTube, WhatsApp-first audiences, and regional product videos. Use Gujarati script when you can; test English brand names inside Gujarati sentences.",
            "Common failure points: transliterated place names, mixed Hindi-Gujarati drafts, and long formal sentences. Shorter spoken sentences almost always sound better.",
            "After export, use <a href=\"/tools/trim-cut-audio\">trim</a>, <a href=\"/tools/merge-audio-files\">merge</a>, or <a href=\"/tools/convert-audio-format\">convert</a>. See also <a href=\"/marathi-text-to-speech\">Marathi TTS</a> and <a href=\"/hindi-text-to-speech\">Hindi TTS</a>.",
        ],
        "steps": [
            "Open Voice Studio and choose Gujarati when available.",
            "Preview on a line from your real niche (product, education, or community update).",
            "Generate a short section first; fix problem words.",
            "Produce remaining sections and download.",
            "Normalize or trim before publishing.",
        ],
        "use_cases": [
            ("Gujarati YouTube & Reels", "Explainers and product demos for Gujarati viewers."),
            ("SME marketing", "Service descriptions and offer videos without hiring VO daily."),
            ("Community content", "Temple, association, and diaspora updates."),
            ("Learning", "Listen-along versions of written Gujarati material."),
        ],
        "faq": [
            ("Is Gujarati TTS free?", "Yes within free-tier limits, no account required to start."),
            ("Gujarati script required?", "Strongly recommended over pure Roman for accuracy."),
            ("Can I mix English product names?", "Yes — test those lines specifically before a full generate."),
            ("Commercial rights?", "Follow current Terms for generated audio."),
            ("Voice list?", "Live catalog inside Voice Studio."),
            ("Related languages?", "Many creators also publish Hindi or Marathi variants of the same outline."),
        ],
        "cta_label": "Open Gujarati voices in Voice Studio",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("Hindi text to speech", "/hindi-text-to-speech"),
            ("Marathi text to speech", "/marathi-text-to-speech"),
            ("All voices", "/voices"),
            ("Free text to speech", "/free-text-to-speech"),
        ],
    },
    "malayalam-text-to-speech": {
        "title": "Malayalam Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Free Malayalam text to speech online. Generate Malayalam AI voiceovers for YouTube, education, and regional content — neural voices, no signup required to start.",
        "eyebrow": "Malayalam AI Voice",
        "h1": "Create a Malayalam voiceover from text",
        "intro": [
            "Malayalam text-to-speech on VoxCraft is for Kerala-focused and global Malayali creators who need downloadable narration — not only browser read-aloud. Paste Malayalam script, preview a neural voice, and export for video or courses.",
            "Malayalam orthography and long compounds can stress weaker TTS engines. Keep sentences shorter for spoken delivery, and always test proper nouns and English tech terms.",
            "Pair with <a href=\"/tamil-text-to-speech\">Tamil TTS</a> if you serve multi-language South Indian audiences, and use free tools to <a href=\"/tools/normalize-audio-volume\">normalize</a> before upload.",
        ],
        "steps": [
            "Open Voice Studio and select Malayalam if listed.",
            "Preview two voices on a real script line.",
            "Generate a short sample; check names and numbers.",
            "Revise, then generate remaining sections.",
            "Download and edit as needed.",
        ],
        "use_cases": [
            ("Malayalam YouTube", "Explainers, reviews, and educational channels."),
            ("Gulf diaspora content", "Updates and tutorials for Malayali audiences abroad."),
            ("Courses", "Audio lessons and revision tracks."),
            ("Product demos", "Consistent regional product voice."),
        ],
        "faq": [
            ("Is Malayalam text to speech free?", "Yes within published free-tier limits."),
            ("Native script?", "Yes — Malayalam script is preferred over Romanized input."),
            ("Commercial use?", "Allowed under current Terms for audio you generate."),
            ("How do I improve quality?", "Shorter sentences, clear punctuation, and section-by-section generation."),
            ("Where are voices listed?", "Voice Studio language selector."),
            ("Related pages?", "Tamil and Kannada TTS pages for neighboring-language workflows."),
        ],
        "cta_label": "Try Malayalam voices in Voice Studio",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("Tamil text to speech", "/tamil-text-to-speech"),
            ("Kannada text to speech", "/kannada-text-to-speech"),
            ("Free text to speech", "/free-text-to-speech"),
            ("Text to speech for YouTube", "/text-to-speech-for-youtube"),
        ],
    },
    "kannada-text-to-speech": {
        "title": "Kannada Text to Speech — Free AI Voice | VoxCraft",
        "meta_description": "Free Kannada text to speech online. Generate Kannada AI voiceovers for YouTube, education, and product videos — neural voices, downloadable audio, no signup to start.",
        "eyebrow": "Kannada AI Voice",
        "h1": "Create a Kannada voiceover from text",
        "intro": [
            "Kannada text-to-speech on VoxCraft targets creators in Karnataka and Kannada-speaking audiences online. Generate neural narration from written Kannada, test delivery on phone speakers, and download files for your editor.",
            "Test English brand names, Bengaluru/Bangalore-style mixed speech, and formal vs casual register. A sample with a price or product line is more diagnostic than a literary sentence.",
            "After TTS, <a href=\"/tools/trim-cut-audio\">trim</a> and <a href=\"/tools/normalize-audio-volume\">normalize</a> as needed. Related: <a href=\"/telugu-text-to-speech\">Telugu TTS</a>, <a href=\"/tamil-text-to-speech\">Tamil TTS</a>.",
        ],
        "steps": [
            "Open Voice Studio and pick Kannada when available.",
            "Preview voices on a niche-specific line.",
            "Generate a short section; fix problem words.",
            "Produce remaining sections labeled by scene.",
            "Export and align to video.",
        ],
        "use_cases": [
            ("Kannada YouTube", "Tech, education, and regional news-style channels."),
            ("Startup & product explainers", "Kannada product stories for local customers."),
            ("Education", "Course and coaching audio in Kannada."),
            ("Multi-language South India", "Kannada alongside Telugu or Tamil versions."),
        ],
        "faq": [
            ("Is Kannada TTS free?", "Yes within free-tier limits; no account required to start."),
            ("Kannada script?", "Prefer native Kannada script over pure Roman."),
            ("Commercial use?", "Follow live Terms for generated audio."),
            ("Numbers or brands sound off?", "Rewrite as words or split the sentence; regenerate only that part."),
            ("Voice catalog?", "Live list in Voice Studio."),
            ("Need higher limits?", "See pricing when free caps block your schedule."),
        ],
        "cta_label": "Open Kannada voices in Voice Studio",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("Telugu text to speech", "/telugu-text-to-speech"),
            ("Tamil text to speech", "/tamil-text-to-speech"),
            ("All voices", "/voices"),
            ("Free text to speech", "/free-text-to-speech"),
        ],
    },
    "remove-noise-from-audio": {
        "title": "Remove Noise from Audio Online — Free | VoxCraft",
        "meta_description": "Remove background noise from audio online. Clean podcasts, interviews, and voiceovers in the browser — free tier, no install. Pair with normalize and convert tools.",
        "eyebrow": "Denoise",
        "h1": "Remove noise from audio online",
        "intro": [
            "Background noise (fans, traffic, room hiss) makes otherwise good takes unusable. VoxCraft’s noise-removal tool targets speech recordings so you can salvage interviews, voiceovers, and phone captures.",
            "Use the dedicated tool at <a href=\"/tools/remove-background-noise\">remove background noise</a>. After cleanup, <a href=\"/tools/normalize-audio-volume\">normalize volume</a> or <a href=\"/tools/convert-audio-format\">convert format</a> for your editor.",
        ],
        "steps": [
            "Upload a speech-focused clip (music beds are a poor fit).",
            "Run denoise and preview the result.",
            "Download, then normalize or trim if needed.",
        ],
        "use_cases": [
            ("Podcast cleanup", "Reduce room noise on remote interviews."),
            ("Voiceover salvage", "Clean a home-recorded take before publishing."),
            ("Pre-TTS prep", "Clean a reference sample before cloning."),
        ],
        "faq": [
            ("Is noise removal free?", "Yes within free tool limits — see the tool page for size caps."),
            ("Does it work on music?", "It is tuned for speech; full music mastering needs a different workflow."),
            ("File size limit?", "Current upload limit is 15MB max for audio tools."),
        ],
        "cta_label": "Remove background noise",
        "related_links": [
            ("Remove background noise tool", "/tools/remove-background-noise"),
            ("Normalize volume", "/tools/normalize-audio-volume"),
            ("Convert audio", "/tools/convert-audio-format"),
            ("Audio tools for YouTubers", "/audio-tools-for-youtubers"),
        ],
    },
    "text-to-speech-mp3": {
        "title": "Text to Speech MP3 Download — Free | VoxCraft",
        "meta_description": "Convert text to speech and download MP3 online. Neural voices in Urdu, Hindi, English and more — free tier, no signup required to start.",
        "eyebrow": "TTS Download",
        "h1": "Text to speech MP3 download",
        "intro": [
            "Generate narration and download an MP3 (or other formats via convert tools) for video editors, LMS uploads, and social posts. VoxCraft focuses on creator export, not just in-browser listening.",
            "Start in <a href=\"/studio\">Voice Studio</a>, then use <a href=\"/tools/convert-audio-format\">convert audio format</a> if you need WAV or another container.",
        ],
        "steps": [
            "Paste text in Voice Studio and choose a voice.",
            "Generate and preview.",
            "Download the file; convert format if your editor requires it.",
        ],
        "use_cases": [
            ("Video editors", "Drop MP3 narration on a timeline."),
            ("Courses", "Upload lesson audio to an LMS."),
        ],
        "faq": [
            ("Can I download without signup?", "Yes on the free tier within limits."),
            ("MP3 vs WAV?", "MP3 is smaller; WAV is higher fidelity for mastering. Convert when needed."),
        ],
        "cta_label": "Generate and download",
        "related_links": [
            ("Voice Studio", "/studio"),
            ("Convert audio format", "/tools/convert-audio-format"),
            ("Free text to speech", "/free-text-to-speech"),
        ],
    },
}


# Fields the admin form (/admin/seo) is allowed to override — matches the
# unified field set admin_seo() saves for both "tool" and "seo" page kinds.
# related_links stays code-only: it's not in admin_seo's save/form-field
# list, so an override would never have it, but we exclude it explicitly
# here too rather than relying on that by omission.
EDITABLE_SEO_FIELDS = (
    "title", "meta_description", "eyebrow", "h1", "sub", "cta_label",
    "intro", "how_it_works", "steps", "tips", "use_cases", "faq",
)


def _load_synced_overrides() -> dict:
    """Load data/page_content_overrides.json, written by the admin panel's
    manual "Push all changes to repo" button (see github_sync.py). Returns
    {} if it doesn't exist yet or is malformed — SEO_PAGES below just keeps
    its hardcoded values in that case, same as before this existed."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "page_content_overrides.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


# Bake the last-synced admin content into SEO_PAGES itself at import time —
# same reasoning as the identical block in tool_pages.py: get_seo_page()
# below merges live DB overrides on top of SEO_PAGES at request time (fast,
# but only as durable as the DB); this merge instead updates the
# code-level baseline once, at process start, so a fresh deploy — even
# with a brand new, empty database — already reflects the last-pushed
# content rather than the original hardcoded copy above.
for _slug, _override in _load_synced_overrides().items():
    if not _slug.startswith("seo:"):
        continue
    _seo_slug = _slug[len("seo:"):]
    _base = SEO_PAGES.get(_seo_slug)
    if not _base:
        continue
    for _key in EDITABLE_SEO_FIELDS:
        if _key in _override and _override[_key] is not None:
            _base[_key] = _override[_key]


def get_seo_page(slug: str):
    """Return the effective SEO landing page dict: code defaults merged
    with any admin override stored in page_content. Returns None if slug
    is unknown. Mirrors tool_pages.get_tool_page() — added for parity and
    so whatever route eventually serves these pages publicly can pull
    live-edited content the same way tool pages already do."""
    base = SEO_PAGES.get(slug)
    if not base:
        return None
    try:
        import persistence
        override = persistence.load_page_content(f"seo:{slug}") or {}
    except Exception:
        override = {}
    out = dict(base)
    for key in EDITABLE_SEO_FIELDS:
        if key in override and override[key] is not None:
            out[key] = override[key]
    return out
