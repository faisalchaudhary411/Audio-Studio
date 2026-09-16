"""Content for VoxCraft's dedicated SEO landing pages.

These pages are informational entry points only. They reuse existing public
routes and tools, so adding or editing a page here cannot change audio, TTS,
payments, accounts, or usage-limit behaviour.
"""

import json
import os

SEO_PAGES = {
    "urdu-text-to-speech": {
        "title": "Urdu Text to Speech — Create Urdu AI Voice Online | VoxCraft",
        "meta_description": "Create Urdu AI voiceovers from text online with VoxCraft. Choose a voice, adjust rate and pitch, and generate narration for videos and other projects.",
        "eyebrow": "Urdu AI Voice",
        "h1": "Create an Urdu voiceover from text",
        "intro": ['Create Urdu AI voiceovers from text online with VoxCraft Voice Studio. Choose an Urdu neural voice, paste your script, adjust rate or pitch if needed, and generate narration for YouTube, courses, or explainers — free tier available with no account required.', 'Urdu text-to-speech is not just “another language slot.” Pronunciation of names, numbers, and mixed English–Urdu lines is where generic global TTS often fails listeners. VoxCraft treats Urdu as a first-class workflow: test short samples, revise spellings, then generate longer sections.', 'A practical creator path: draft the script → generate 20–40 seconds → listen on phone speakers → fix hard words → generate the rest → optionally clean or convert the file with free <a href="/tools">audio tools</a>. For YouTube-specific structure, see <a href="/text-to-speech-for-youtube">text to speech for YouTube</a> and <a href="/how-to-create-youtube-voiceover">how to create a YouTube voiceover</a>.', 'Commercial use of audio you generate is allowed under current Terms, subject to those terms and any rights in material you upload. Always verify live pricing limits on the pricing page before committing a high-volume channel.'],
        "steps": ['Open Voice Studio and select Urdu from the language list.', 'Preview two or three voices on the same short line from your real script.', 'Paste a short section first (opening paragraph), generate, and listen for names and numbers.', 'Revise spellings or punctuation where needed, then generate remaining sections.', 'Download and, if required, trim, merge, or convert with VoxCraft audio tools before editing video.'],
        "use_cases": [('YouTube narration', 'Faceless and explainer channels that need steady Urdu voiceover without daily studio time.'), ('Learning content', 'Turn written Urdu lessons or notes into audio for listening practice.'), ('Creator drafts', 'Hear a script before hiring talent or recording yourself.'), ('Localization', 'Produce Urdu versions of English outlines when you already have the written translation.')],
        "faq": [('Is Urdu text to speech free on VoxCraft?', 'Yes. You can try Urdu voices on the free tier without creating an account, within published usage limits. See pricing for Pro limits.'), ('Which Urdu voice should I pick?', 'Preview with a line from your actual niche (news, education, story). The “best” voice depends on audience age and formality.'), ('Can I mix English words in an Urdu script?', 'Yes, but mixed lines need testing. Generate a short sample that includes the English terms you care about.'), ('Nastaliq vs Roman Urdu — what should I type?', 'Native script usually produces more reliable pronunciation than pure Roman Urdu. If you only have Roman, test carefully.'), ('Can I use the audio on monetized YouTube?', 'Audio you generate is yours to use commercially under current Terms — confirm the Terms page for details.'), ('How do I avoid robotic delivery?', 'Use natural punctuation, shorter sentences, and section-by-section generation instead of one giant block.'), ('Where do I go after generating audio?', 'Common next steps: trim, merge, denoise, or convert format in the free toolset, then drop into your editor.'), ('How is this different from global TTS sites?', 'Many tools add Urdu late. VoxCraft prioritizes South Asian creator workflows alongside English, with tools around the voiceover, not only a single generate button.')],
        "cta_label": "Try Urdu voices in Voice Studio",
    },
        "related_links": [('Open Voice Studio', '/studio'), ('Free text to speech', '/free-text-to-speech'), ('Text to speech for YouTube', '/text-to-speech-for-youtube'), ('Hindi text to speech', '/hindi-text-to-speech'), ('Remove background noise', '/tools/remove-background-noise'), ('Convert audio format', '/tools/convert-audio-format')],
    
    "hindi-text-to-speech": {
        "title": "Hindi Text to Speech — Create Hindi AI Voice Online | VoxCraft",
        "meta_description": "Create Hindi AI voiceovers from text online with VoxCraft. Select a Hindi voice, adjust delivery, and generate narration for videos and other projects.",
        "eyebrow": "Hindi AI Voice", "h1": "Create a Hindi voiceover from text",
        "intro": ['Create Hindi AI voiceovers from text online with VoxCraft. Select a Hindi neural voice, enter Devanagari script where possible, and generate narration for videos, courses, and explainers — free tier available without required signup.', 'Hindi TTS quality shows up on names, numbers, and English loanwords inside Hindi sentences. Always test a short real sample before generating a full episode-length script.', 'Pair generation with creator tools when needed: <a href="/tools/trim-cut-audio">trim</a>, <a href="/tools/merge-audio-files">merge</a>, <a href="/tools/normalize-audio-volume">normalize loudness</a>, or <a href="/tools/remove-background-noise">denoise</a> if you recorded something alongside AI narration.', 'For bilingual channels, keep Urdu and Hindi tests separate rather than assuming one voice setting fits both audiences. See also <a href="/urdu-text-to-speech">Urdu text to speech</a> and <a href="/text-to-speech-for-youtube">TTS for YouTube</a>.'],
        "steps": ['Open Voice Studio and choose Hindi.', 'Preview voices on a line that includes a name and a number.', 'Generate a short opening section first.', 'Adjust rate/pitch if available, then produce remaining sections.', 'Export and assemble in your video editor.'],
        "use_cases": [('YouTube explainers', 'Hindi narration for educational and product videos.'), ('Courses', 'Audio versions of written lessons.'), ('Drafting', 'Hear pacing before a live record session.')],
        "faq": [('Is Hindi TTS free?', 'Yes within free-tier limits, no account required to start.'), ('Should I use Devanagari?', 'Yes when you can — native script usually improves pronunciation versus pure Roman Hindi.'), ('Commercial use?', 'Allowed under current Terms for audio you generate; check Terms for full rules.'), ('Can I combine with voice cloning?', 'Voice cloning is a separate Pro+ workflow. Stock Hindi neural voices are available in Studio on free/Pro tiers as published.'), ('How long should test samples be?', '20–40 seconds of real script beats a single marketing demo line.'), ('What if numbers sound wrong?', 'Rewrite numbers as words or restructure the sentence and regenerate that clause only.'), ('Where is the full voice list?', 'Inside Voice Studio’s language and voice selectors — the live list is authoritative.')],
        "cta_label": "Try Hindi voices in Voice Studio",
    },
        "related_links": [('Voice Studio', '/studio'), ('Urdu text to speech', '/urdu-text-to-speech'), ('Free TTS', '/free-text-to-speech'), ('YouTube voiceover guide', '/how-to-create-youtube-voiceover'), ('Normalize volume', '/tools/normalize-audio-volume')],
    
    "punjabi-text-to-speech": {
        "title": "Punjabi Text to Speech — Create Punjabi AI Voice Online | VoxCraft",
        "meta_description": "Create Punjabi AI voiceovers from text online with VoxCraft. Explore the available voice options and generate narration for creator projects.",
        "eyebrow": "Punjabi AI Voice", "h1": "Turn Punjabi text into spoken narration",
        "intro": ["Use VoxCraft Voice Studio to test Punjabi text with the Punjabi voice options currently available in the library.", "Because pronunciation depends on the exact text and voice, listen to a short sample before relying on generated audio for an important project."],
        "steps": ["Open Voice Studio.", "Choose Punjabi and select a voice.", "Enter a short test script first.", "Review the result, then generate your full narration when you are satisfied."],
        "use_cases": [("Regional content", "Create narration for videos aimed at Punjabi-speaking audiences."), ("Script review", "Hear a written script before a final recording session."), ("Creative projects", "Experiment with pacing and narration style.")],
        "faq": [("Is Punjabi available in VoxCraft?", "Check the live voice library in Voice Studio for the current Punjabi options."), ("How can I improve pronunciation?", "Use clear spelling and punctuation, then test difficult names and terms in short samples."), ("Do I need an account to start?", "No account is required for the free-tier workflow.")],
        "cta_label": "Open Punjabi voices",
    },
    "bengali-text-to-speech": {
        "title": "Bengali Text to Speech — Create Bengali AI Voice Online | VoxCraft",
        "meta_description": "Create Bengali AI voiceovers from text online with VoxCraft. Select an available voice and generate narration for videos, learning and creator projects.",
        "eyebrow": "Bengali AI Voice", "h1": "Create Bengali narration from text",
        "intro": ["VoxCraft Voice Studio gives you a simple way to test written Bengali with the Bengali voices currently available in the library.", "Start with a short section of your script so you can review pronunciation and pacing before producing a longer piece."],
        "steps": ["Open Voice Studio.", "Select Bengali and an available voice.", "Paste a short sample of your script.", "Generate and review before continuing with the full narration."],
        "use_cases": [("YouTube videos", "Create Bengali narration for explainers and creator content."), ("Learning material", "Listen to written material in an audio format."), ("Content drafts", "Check how a script sounds before publishing.")],
        "faq": [("Can I test Bengali voices before a long project?", "Yes. A short test is recommended for checking pronunciation and delivery."), ("Is the tool browser-based?", "VoxCraft runs through the web interface, so you do not need to install a desktop editor for this workflow."), ("Where do I see current voices?", "Open Voice Studio and check the voice and language selectors.")],
        "cta_label": "Try Bengali voices",
    },
    "tamil-text-to-speech": {
        "title": "Tamil Text to Speech — Create Tamil AI Voice Online | VoxCraft",
        "meta_description": "Create Tamil AI voiceovers from text online with VoxCraft. Select an available Tamil voice and generate narration for videos, learning and creator projects.",
        "eyebrow": "Tamil AI Voice", "h1": "Create Tamil narration from text",
        "intro": ["VoxCraft Voice Studio gives you a simple way to test written Tamil with the Tamil voices currently available in the library.", "Start with a short section of your script so you can review pronunciation and pacing before producing a longer piece."],
        "steps": ["Open Voice Studio.", "Select Tamil and an available voice.", "Paste a short sample of your script.", "Generate and review before continuing with the full narration."],
        "use_cases": [("YouTube videos", "Create Tamil narration for explainers and creator content."), ("Learning material", "Listen to written material in an audio format."), ("Content drafts", "Check how a script sounds before publishing.")],
        "faq": [("Can I test Tamil voices before a long project?", "Yes. A short test is recommended for checking pronunciation and delivery."), ("Is the tool browser-based?", "VoxCraft runs through the web interface, so you do not need to install a desktop editor for this workflow."), ("Where do I see current voices?", "Open Voice Studio and check the voice and language selectors.")],
        "cta_label": "Try Tamil voices",
    },
    "telugu-text-to-speech": {
        "title": "Telugu Text to Speech — Create Telugu AI Voice Online | VoxCraft",
        "meta_description": "Create Telugu AI voiceovers from text online with VoxCraft. Select an available Telugu voice and generate narration for videos, learning and creator projects.",
        "eyebrow": "Telugu AI Voice", "h1": "Create Telugu narration from text",
        "intro": ["VoxCraft Voice Studio gives you a simple way to test written Telugu with the Telugu voices currently available in the library.", "Start with a short section of your script so you can review pronunciation and pacing before producing a longer piece."],
        "steps": ["Open Voice Studio.", "Select Telugu and an available voice.", "Paste a short sample of your script.", "Generate and review before continuing with the full narration."],
        "use_cases": [("YouTube videos", "Create Telugu narration for explainers and creator content."), ("Learning material", "Listen to written material in an audio format."), ("Content drafts", "Check how a script sounds before publishing.")],
        "faq": [("Can I test Telugu voices before a long project?", "Yes. A short test is recommended for checking pronunciation and delivery."), ("Is the tool browser-based?", "VoxCraft runs through the web interface, so you do not need to install a desktop editor for this workflow."), ("Where do I see current voices?", "Open Voice Studio and check the voice and language selectors.")],
        "cta_label": "Try Telugu voices",
    },
    "text-to-speech-for-youtube": {
        "title": "Text to Speech for YouTube Videos — AI Voiceover Workflow | VoxCraft",
        "meta_description": "Learn a practical text-to-speech workflow for YouTube videos: prepare a script, test voices, review pronunciation, and create narration with VoxCraft.",
        "eyebrow": "YouTube Voiceover", "h1": "Use text to speech for YouTube narration",
        "intro": ['Use text to speech for YouTube narration with a workflow built for creators: write for the ear, test a short opening, generate in sections, then edit. VoxCraft Voice Studio supports multilingual neural voices including Urdu and Hindi, with a free tier that does not require signup.', 'TTS fails on YouTube when people generate a 10-minute monologue in one click and skip listening. Treat AI voice like a voice actor take: short tests, revisions, then full generate.', 'After audio is ready, creators often <a href="/tools/normalize-audio-volume">normalize loudness</a>, <a href="/tools/trim-cut-audio">trim</a>, or <a href="/tools/merge-audio-files">merge</a> intros and outros. For language-specific landing pages see <a href="/urdu-text-to-speech">Urdu</a> and <a href="/hindi-text-to-speech">Hindi</a>.', 'Faceless channels, explainers, and product reviews are the common fits. Documentary-style emotional performance may still need human VO — TTS is a production tool, not a guarantee of cinematic acting.'],
        "steps": ['Finish and proofread the script for spoken delivery.', 'Generate only the first 20–40 seconds and listen on phone speakers.', 'Fix names, numbers, and awkward phrases.', 'Generate remaining sections; keep files labeled by scene.', 'Trim/merge/normalize as needed, then align to the timeline.'],
        "use_cases": [('Faceless YouTube', 'Consistent narration without daily recording.'), ('Explainers', 'Steady educational delivery.'), ('Multilingual channels', 'Urdu/Hindi/English variants of the same outline.')],
        "faq": [('Is TTS allowed on monetized YouTube?', 'YouTube allows AI-assisted content under its policies when you follow their rules; also follow VoxCraft Terms. Policies evolve — verify on YouTube Help.'), ('Should I generate the whole video at once?', 'Section-by-section is safer for quality control and easier retakes.'), ('What loudness should I aim for?', 'Many creators normalize toward platform expectations; use the <a href="/tools/normalize-audio-volume">normalize tool</a> and check on multiple devices.'), ('Urdu or Hindi for my audience?', 'Match the audience language; test both if your channel is bilingual.'), ('Free tier enough for weekly uploads?', 'Depends on length and frequency. Watch in-product limits; upgrade when caps block your schedule.'), ('How do I make TTS less obvious?', 'Natural punctuation, moderate speed, and human editing of the script matter more than any single “emotion” toggle.'), ('Can I combine TTS with my real voice?', 'Yes — common hybrid: AI for drafts or secondary languages, human for flagship episodes.')],
        "cta_label": "Create a YouTube voiceover",
    },
        "related_links": [('Voice Studio', '/studio'), ('How to create a YouTube voiceover', '/how-to-create-youtube-voiceover'), ('Audio tools for YouTubers', '/audio-tools-for-youtubers'), ('Normalize volume', '/tools/normalize-audio-volume'), ('Merge audio', '/tools/merge-audio-files')],
    
    "free-text-to-speech": {
        "title": "Free Text to Speech Online — Try AI Voice Generation | VoxCraft",
        "meta_description": "Try VoxCraft's free text-to-speech workflow online. Choose an available voice, enter text, and generate narration within the current free-tier limits.",
        "eyebrow": "Free TTS", "h1": "Try text to speech online for free",
        "intro": ['Try free text to speech online with VoxCraft — no account required on the free tier. Choose a language and neural voice, paste text, generate narration, and download within published limits.', '“Free TTS” tools differ on three things that matter: voice quality, language coverage, and whether commercial use is allowed. VoxCraft is built for creators who need usable multilingual narration (including Urdu and Hindi) plus free utilities around the file.', 'Use free generation to test scripts and ship small projects. Move to Pro when daily limits block your publishing schedule. See <a href="/pricing">pricing</a> for current numbers rather than screenshots from older posts.', 'Next reads: <a href="/urdu-text-to-speech">Urdu TTS</a>, <a href="/hindi-text-to-speech">Hindi TTS</a>, <a href="/text-to-speech-for-youtube">TTS for YouTube</a>, and the <a href="/tools">audio tools directory</a>.'],
        "steps": ['Open Voice Studio without creating an account.', 'Pick language and voice; preview a sample.', 'Paste a short test script and generate.', 'Download and review on phone speakers.', 'Check pricing if you need higher limits or Pro+ features like cloning.'],
        "use_cases": [('Quick tests', 'Compare voices on the same paragraph.'), ('Small projects', 'Ship short videos within free limits.'), ('Education', 'Teachers and students testing narration ideas.')],
        "faq": [('Do I need a credit card for free TTS?', 'No. Free tier does not require signup or a card to start.'), ('Is free audio commercial-friendly?', 'Generated audio is usable commercially under current Terms — always read the live Terms page.'), ('What are the free limits?', 'Limits can change. The Studio UI and pricing page show current daily/monthly allowances.'), ('Free vs Pro — when to upgrade?', 'Upgrade when you hit caps, need batch volume, or want Pro+ features such as voice cloning.'), ('Which languages are free?', 'Free tier includes access to the Studio voice library subject to usage caps; Urdu and Hindi are first-class options.'), ('Can I remove watermarks?', 'VoxCraft does not market TTS downloads as watermarked promo files; you get the generated audio file under the plan rules.'), ('How does this compare to TTSMaker or browser read-aloud?', 'Browser read-aloud is for listening, not always for exportable creator workflows. VoxCraft focuses on downloadable narration plus editing tools.')],
        "cta_label": "Try text to speech",
    },
        "related_links": [('Voice Studio', '/studio'), ('Urdu TTS', '/urdu-text-to-speech'), ('Hindi TTS', '/hindi-text-to-speech'), ('YouTube TTS workflow', '/text-to-speech-for-youtube'), ('All tools', '/tools')],
    
    "how-to-create-youtube-voiceover": {
        "title": "How to Create a YouTube Voiceover — Step-by-Step Workflow | VoxCraft",
        "meta_description": "Learn a practical YouTube voiceover workflow from script preparation and voice testing to audio review, editing and final export.",
        "eyebrow": "Creator Guide", "h1": "How to create a YouTube voiceover",
        "intro": ["A reliable voiceover workflow starts before you open a voice tool. A clean script, short test, and deliberate review process can prevent repeated fixes later in editing.", "The exact workflow works whether you use an AI voice or record your own voice: prepare, test, review, edit, then match the final audio to the video."],
        "steps": ["Write for the ear, using short and natural sentences.", "Test the first 20–40 seconds before producing the full narration.", "Correct names, numbers, pacing and difficult phrases.", "Generate or record the final sections, then trim and merge them as needed.", "Listen once with the finished video before export."],
        "use_cases": [("New creators", "Create a repeatable process instead of improvising each video."), ("Faceless videos", "Keep narration production separate from the visual edit."), ("Team workflows", "Use the script as the source of truth for revisions and replacements.")],
        "faq": [("What should I test first?", "Test the opening and any line containing names, dates, numbers or unusual words."), ("Why split narration into sections?", "Small sections are easier to replace without regenerating or re-recording an entire project."), ("What comes after narration?", "Review the final timing against the video, then make any small edits before export.")],
        "cta_label": "Open Voice Studio",
    },
    "audio-tools-for-youtubers": {
        "title": "Audio Tools for YouTubers — Practical Online Audio Workflow | VoxCraft",
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
