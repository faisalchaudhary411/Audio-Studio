"""
Content and metadata for VoxCraft's individual tool pages (/tools/<slug>).

Why this exists: the tools used to live only as tabs on one /tools page, all
sharing a single URL. Google (and AdSense's content reviewer) never saw them
as distinct pages, and each tab had almost no unique text around the widget
itself — a common "thin/low-value content" pattern for AI tool sites.

This module gives each tool its own indexable URL and enough real, specific
written content (how it works, use cases, tips, FAQ) to stand on its own as
a page, while the actual widget markup is still shared from
templates/partials/tool_widgets/<widget>.html so there's no duplicated UI
code to keep in sync.

To add a new tool page: add an entry here, drop its widget partial in
templates/partials/tool_widgets/, and it's automatically routed, sitemapped,
and cross-linked — nothing else to touch.
"""

import json
import os

TOOL_PAGES = {
    "transcribe-audio-to-text": {
        "widget": "transcribe",
        "usage_key": "transcribe",
        "title": "Urdu & Hindi Speech to Text — Free | VoxCraft",
        "meta_description": "Transcribe Urdu, Hindi, or English audio to text online free. WAV, MP3, M4A, OGG, FLAC for captions and notes.",
        "eyebrow": "Audio → Text",
        "h1": "Transcribe Urdu, Hindi, or English audio to text — free",
        "sub": "Upload a recording and get a text transcript back, with Urdu and Hindi as first-choice languages. No install, no account required for free-tier use.",
        "intro": [
            'Transcribe Urdu, Hindi, or English audio to text online for free with VoxCraft. Upload a WAV, MP3, M4A, OGG or FLAC recording and get a readable transcript — no install and no account required on the free tier.',
            'Transcription turns spoken audio into searchable text: the step between “I have a recording” and “I can edit, quote, or publish.” Creators use it for interviews, lectures, voice memos, and podcasts. Urdu and Hindi sit near the top of the language choices here — not buried as an afterthought.',
            'Accuracy depends on audio quality more than any single brand name. A quiet mic and clear speakers outperform a noisy café recording on every engine. That is why many workflows pair this tool with <a href="/tools/remove-background-noise" style="color:var(--brass-hi)">background noise removal</a> first, then transcribe.',
            'VoxCraft accepts common formats up to the current upload limit and can process longer clips in chunks so a 20-minute interview is handled the same way as a short memo. After you have text, you can draft captions, blog outlines, or study notes without re-listening to the whole file.',
        ],
        "how_it_works": [
            "Upload your audio file (WAV, MP3, M4A, OGG or FLAC, 15MB max).",
            "Pick the spoken language from the dropdown — Urdu and Hindi are listed first, or choose auto-detect. Matching the language improves accuracy.",
            "Tap Transcribe and wait a few seconds to a minute depending on length.",
            "Review the text, then copy it or download it as a .txt file.",
        ],
        "use_cases": [
            ("Urdu & Hindi podcasters", "Turn an Urdu or Hindi episode into a blog post or show notes without re-typing everything by hand."),
            ("Students", "Convert a recorded lecture into text you can search, highlight, and study from."),
            ("Journalists & researchers", "Get a rough transcript of an interview to quote from, then verify the exact wording against the audio."),
            ("Meeting notes", "Record a call and get a working transcript to build minutes from."),
        ],
        "tips": [
            'Denoise noisy sources before transcribing when the room tone is strong.',
            'Prefer higher-bitrate source files when you still have them; heavy compression can blur consonants.',
            'Speak one language at a time when possible — rapid code-switching is harder for every ASR system.',
            'For interviews, leave short pauses between speakers so turn-taking is clearer in the transcript.',
            'Use the transcript as a draft: fix names and technical terms before publishing.',
            'Need only a section? <a href="/tools/trim-cut-audio" style="color:var(--brass-hi)">Trim</a> first to save time and quota.',
        ],
        "faq": [
            ('Which languages work best?', 'English, Urdu, and Hindi are primary targets for this tool’s positioning. Other languages may be available depending on the recognition path in use — always test a short sample of your real accent and vocabulary.'),
            ('Is transcription free?', 'Yes within free-tier limits, with no account required to start. Heavy daily use may hit quotas; see <a href="/pricing" style="color:var(--brass-hi)">pricing</a> for Pro options.'),
            ('How accurate is it on noisy audio?', 'Accuracy drops with overlapping speech, loud music, and strong reverb. Clean the file with <a href="/tools/remove-background-noise" style="color:var(--brass-hi)">Remove background noise</a> when the problem is steady hum or hiss.'),
            ('What formats can I upload?', 'Common formats such as WAV, MP3, M4A, OGG, and FLAC, subject to the current size limit shown in the uploader.'),
            ('Can I transcribe a long podcast episode?', 'Longer files are processed in chunks. Very long episodes may need splitting with the <a href="/tools/trim-cut-audio" style="color:var(--brass-hi)">cutter</a> or <a href="/tools/split-audio-by-silence" style="color:var(--brass-hi)">split by silence</a> tool.'),
            ('Does it add punctuation automatically?', 'Punctuation quality varies by language and model path. Treat the output as an editable draft, especially for formal publishing.'),
            ('Is this the same as live captions?', 'No. This is file-based transcription of an upload, not a real-time captioning app for meetings.'),
            ('How do creators use transcripts with YouTube?', 'Many paste cleaned transcripts into descriptions or as a draft for subtitles. Pair with <a href="/text-to-speech-for-youtube" style="color:var(--brass-hi)">text to speech for YouTube</a> if you are generating narration the other direction.'),
        ],
        "related_tools": ["remove-background-noise", "convert-audio-format", "extract-audio-from-video"],
        "blog_keywords": ["transcri", "speech to text", "subtitle"],
    },
    "convert-audio-format": {
        "widget": "convert",
        "usage_key": "convert",
        "title": "Convert Audio Format Online Free | VoxCraft",
        "meta_description": "Convert audio format online free. Change between MP3, WAV, OGG, M4A and FLAC with adjustable bitrate. No install, no signup.",
        "eyebrow": "Format Conversion",
        "h1": "Convert audio format online — free",
        "sub": "Change format and bitrate in one step — useful when a platform, editor, or device only accepts a specific file type.",
        "intro": [
            'Convert audio format online for free with VoxCraft. Change between MP3, WAV, OGG, FLAC and other common formats in the browser — pick an output type and bitrate, then download. No install or signup required on the free tier.',
            'Format conversion is a utility job, not a magic quality upgrade. Converting a low-bitrate MP3 to WAV does not restore lost detail; it only changes the container/encoding. Use conversion when a video editor, podcast host, or client specifies a format you do not have yet.',
            'Creators often convert after <a href="/tools/extract-audio-from-video" style="color:var(--brass-hi)">extracting audio from video</a>, after generating speech in <a href="/studio" style="color:var(--brass-hi)">Voice Studio</a>, or before merging clips. Keeping a lossless master (WAV/FLAC) while exporting MP3 for delivery is a common professional habit.',
            'VoxCraft keeps the tool focused: one file at a time, clear format choices, browser-based. For batch library migration of hundreds of tracks, a local script or DAW batch exporter may still be faster.',
        ],
        "how_it_works": [
            "Upload your source file (WAV, MP3, OGG, M4A or FLAC, 15MB max).",
            "Choose the output format from the dropdown.",
            "For MP3/OGG/M4A output, set the bitrate — higher means better quality and a larger file.",
            "Tap Convert and download the result.",
        ],
        "use_cases": [
            ("Podcast hosting", "Convert a WAV master down to a smaller MP3 at 128–192 kbps for faster hosting and streaming."),
            ("Video editors", "Convert MP3 voiceovers to WAV, since some editing software handles uncompressed audio more reliably."),
            ("Archiving", "Convert a compressed file to FLAC when you want a lossless copy for long-term storage — note this won't restore quality already lost to compression."),
            ("Compatibility", "Convert to whatever format a specific app, device or platform requires."),
        ],
        "tips": [
            'Do not expect MP3→WAV to improve fidelity; keep originals when quality matters.',
            'For speech voiceovers, 128–192 kbps MP3 is usually enough; music often wants higher.',
            'Convert after denoising when the source is noisy.',
            'Name files clearly (project_scene_v3.wav) so version chaos does not creep in.',
        ],
        "faq": [
            ('Which formats are supported?', 'Common speech and production formats such as MP3, WAV, OGG, and FLAC. Check the tool UI for the live list.'),
            ('Is conversion free?', 'Yes within free-tier limits, no account required to start.'),
            ('Does converting to FLAC improve a poor MP3?', 'No. Lossless formats preserve what is already there; they do not invent missing high frequencies.'),
            ('What bitrate should I use for YouTube voiceover?', 'For speech, 160–192 kbps MP3 is a practical default. Always do a short listen on phone speakers.'),
            ('Can I batch-convert many files?', 'This tool is one file at a time. Repeat uploads or use a local batch tool for large libraries.'),
            ('Should I convert before or after merging?', 'Prefer a consistent format before <a href="/tools/merge-audio-files" style="color:var(--brass-hi)">merge</a> when possible so sample rates align cleanly.'),
            ('Is there quality loss every conversion?', 'Repeated lossy→lossy encodes accumulate damage. Minimize generations; keep a lossless master.'),
        ],
        "related_tools": ["compress-audio", "trim-cut-audio", "extract-audio-from-video", "merge-audio-files"],
        "blog_keywords": ["format", "mp3", "convert", "bitrate"],
    },
    "compress-audio": {
        "widget": "compress",
        "usage_key": "compress",
        "title": "Compress Audio Online Free — Shrink Files | VoxCraft",
        "meta_description": "Compress audio online free. Shrink MP3, WAV, OGG, M4A or FLAC for email and uploads — three quality levels.",
        "eyebrow": "Shrink File Size",
        "h1": "Compress audio — reduce file size online, free",
        "sub": "Pick a compression level and get a smaller file back in seconds. No install, no account required.",
        "intro": [
            "Compress an audio file online for free with VoxCraft. Upload an MP3, WAV, OGG, M4A or FLAC file, pick a compression level, and get a smaller file back — useful when an email attachment limit, an upload cap, or plain storage space is the problem, not the audio quality itself.",
            "Compression re-encodes the file at a lower bitrate. That always trades some quality for size — the question is how much you can afford to lose for what you're using the file for. A voice memo you're sharing in a chat can usually take the maximum setting without anyone noticing; a music track you care about should stay on the lighter end.",
            "Every input format gets converted to MP3, since that's the practical standard for small file size. If you're starting from an already-compressed MP3, compressing again re-encodes on top of the existing loss — expect more noticeable quality loss than compressing a WAV or FLAC source the first time.",
        ],
        "how_it_works": [
            "Upload your audio file (WAV, MP3, M4A, OGG or FLAC, 15MB max).",
            "Choose a compression level — Light, Medium, or Maximum.",
            "Tap Compress and wait a few seconds.",
            "Check the size before/after shown, then download the result.",
        ],
        "use_cases": [
            ("Email attachments", "Shrink a recording below an inbox's attachment size limit without needing a file-sharing link."),
            ("Upload limits", "Get a file under a form's or platform's upload cap when the original is too large."),
            ("Storage cleanup", "Reduce the size of old recordings you want to keep but don't need at full quality."),
            ("Faster sharing", "Send a smaller file over a slow connection or a messaging app that compresses large attachments poorly anyway."),
        ],
        "tips": [
            "Light (128 kbps) is usually safe for anything you'd still want to sound good — voiceovers, music you care about.",
            "Maximum (64 kbps) is fine for voice memos and reference recordings where clarity matters more than fidelity.",
            "Compressing an already-compressed MP3 stacks quality loss — start from the original source file when you still have it.",
            "Need the opposite — turn a compressed file into an uncompressed WAV? Use <a href=\"/tools/decompress-audio\" style=\"color:var(--brass-hi)\">Decompress</a> instead.",
        ],
        "faq": [
            ("Will this reduce sound quality?", "Yes, to some degree — that's the tradeoff for a smaller file. Light loses the least; Maximum shrinks the most but is the most audible."),
            ("What output format do I get?", "MP3, regardless of what format you uploaded — it's the practical standard for a small file size."),
            ("Is compressing free?", "Yes within free-tier limits, no account required to start."),
            ("How much smaller will my file get?", "Depends on the original bitrate and the level you pick — the result screen shows the exact before/after size and percentage saved for your specific file."),
            ("Can I compress a file that's already MP3?", "Yes, though re-encoding an already-lossy file loses more noticeably than compressing a WAV or FLAC source the first time."),
            ("Is there a file size limit to upload?", "Yes, 15MB max per file."),
        ],
        "related_tools": ["decompress-audio", "convert-audio-format", "trim-cut-audio"],
        "blog_keywords": ["compress", "reduce file size", "shrink", "smaller file"],
    },
    "decompress-audio": {
        "widget": "decompress",
        "usage_key": "decompress",
        "title": "Decompress Audio to WAV Online Free — MP3 to WAV | VoxCraft",
        "meta_description": "Decompress a compressed audio file (MP3, OGG, M4A) into an uncompressed WAV online, free. No install, no signup required.",
        "eyebrow": "To Uncompressed WAV",
        "h1": "Decompress audio to WAV — free",
        "sub": "Turn a compressed file into an uncompressed WAV for editing or archiving. No install, no account required.",
        "intro": [
            "Decompress a compressed audio file into an uncompressed WAV online for free with VoxCraft. Upload an MP3, OGG, M4A, AAC or similar lossy file and get back a standard WAV — useful when an editor, DAW, or another tool works better with (or requires) an uncompressed source.",
            "One thing worth being upfront about: decompressing doesn't restore quality that's already gone. Lossy formats like MP3 permanently discard some audio detail at the moment they're first encoded — turning that MP3 into a WAV afterward can't bring that detail back, it just stops any further quality loss from happening on top of it during your next round of editing or re-encoding.",
            "Where this genuinely helps: editing software that behaves better with WAV input, avoiding a second generation of lossy re-encoding when you'll be exporting to a compressed format again later, or simply wanting an uncompressed file to work with even if the underlying quality ceiling was already set by the original compression.",
        ],
        "how_it_works": [
            "Upload your compressed audio file (MP3, OGG, M4A, AAC, WMA — 15MB max).",
            "Tap Decompress to WAV.",
            "Wait a few seconds while it decodes.",
            "Download the uncompressed WAV file.",
        ],
        "use_cases": [
            ("Editing in a DAW", "Get a WAV source for editors/DAWs that expect or work better with uncompressed audio."),
            ("Avoiding double compression", "Decode once to WAV before further editing, instead of re-encoding an already-lossy file repeatedly."),
            ("Format compatibility", "Convert to WAV for a tool, plugin, or workflow step that doesn't accept compressed formats."),
        ],
        "tips": [
            "This can't undo quality already lost in the original compression — treat it as a format change, not a quality upgrade.",
            "If you still have the original uncompressed source (before it was ever compressed), use that instead of decompressing the compressed copy.",
            "Need to go the other way — shrink a file's size? Use <a href=\"/tools/compress-audio\" style=\"color:var(--brass-hi)\">Compress</a> instead.",
        ],
        "faq": [
            ("Does this restore quality lost when the file was compressed?", "No. Lossy compression permanently discards detail at encode time; decompressing to WAV can't recreate what's gone — it only stops further loss from here on."),
            ("What formats can I decompress?", "Common lossy formats such as MP3, OGG, M4A, AAC, and WMA."),
            ("Why would I want a bigger, uncompressed file?", "Some editors, DAWs, and workflow steps expect or work better with uncompressed WAV input than with a compressed format."),
            ("Is decompressing free?", "Yes within free-tier limits, no account required to start."),
            ("Is there a file size limit to upload?", "Yes, 15MB max per file."),
        ],
        "related_tools": ["compress-audio", "convert-audio-format", "trim-cut-audio"],
        "blog_keywords": ["decompress", "mp3 to wav", "uncompress", "lossless"],
    },
    "merge-audio-files": {
        "widget": "merge",
        "usage_key": "merge",
        "title": "Merge Audio Files Online Free — Joiner | VoxCraft",
        "meta_description": "Free online audio joiner. Merge audio files and combine multiple MP3, WAV or OGG clips into one track with optional silence gap. No install, no signup.",
        "eyebrow": "Combine Clips",
        "h1": "Merge audio files online — free",
        "sub": "Stitch clips together in order, with a configurable gap between them — no editing software required.",
        "intro": [
            "Merge audio files online for free with VoxCraft. Combine multiple MP3, WAV or OGG clips into one continuous track with an optional silence gap between them — no install or signup required. Merging is the fastest way to stitch together intro + main content + outro, or combine several voice memos into one file, without opening a full editor.",
            "Add files one at a time or in batches — each pick adds to your list rather than replacing it, so you can build up a queue before merging.",
        ],
        "how_it_works": [
            "Tap \"Add files\" and select one or more clips (repeat as needed to build your list).",
            "Reorder by removing and re-adding if needed — files merge in the order shown.",
            "Set the silence gap between clips (0–3000ms) and choose an output format.",
            "Tap Merge audio and download the combined file.",
        ],
        "use_cases": [
            ("Podcast production", "Combine an intro jingle, the main recording, and an outro into one deliverable file."),
            ("Audiobook chapters", "Stitch multiple recording sessions of the same chapter into one continuous track."),
            ("Voice memos", "Combine several short recordings into a single file for easier storage or sharing."),
            ("YouTube narration", "Merge separately-recorded voiceover segments in the right order before syncing to video."),
        ],
        "tips": [
            "A small gap (300–600ms) between clips usually sounds more natural than 0ms, which can make transitions feel abrupt.",
            "Keep source files in a consistent format going in — mixing very different sample rates can occasionally affect the output.",
            "If a clip needs trimming before merging, run it through <a href=\"{cutter_url}\" style=\"color:var(--brass-hi)\">Cutter</a> first.",
        ],
        "faq": [
            ("Is there a limit on how many files I can merge?", "No hard limit on count, but each individual file must be under 15MB."),
            ("Can I reorder files after adding them?", "Currently you remove and re-add in the order you want — files merge top to bottom as listed."),
            ("What output formats are available?", "MP3, WAV, or OGG."),
        ],
        "related_tools": ["trim-cut-audio", "convert-audio-format", "remove-background-noise"],
        "blog_keywords": ["merge", "combine", "stitch"],
    },
    "trim-cut-audio": {
        "widget": "cutter",
        "usage_key": "cutter",
        "title": "Trim & Cut Audio Online Free — MP3 Cutter | VoxCraft",
        "meta_description": "Trim audio online free. Cut MP3/WAV to exact points or split a file — browser MP3 cutter, no install.",
        "eyebrow": "Trim / Split",
        "h1": "Trim and cut audio online — free",
        "sub": "Cut down to exactly the range you need, or split one file into two at a chosen point.",
        "intro": [
            "Trim or cut audio online for free with VoxCraft. Set a start and end time to keep only the part you need, or split one file into two at a chosen timestamp — no desktop editor required. Upload a file and the tool reads its duration automatically, so you can see exactly how much room you have to work with before setting your times.",
        ],
        "how_it_works": [
            "Upload your file — its duration is detected automatically.",
            "Choose Trim (keep a start–end range) or Split (break into two files at one point).",
            "Enter times in seconds, then tap Run.",
            "Download the trimmed file, or both halves if you split.",
        ],
        "use_cases": [
            ("Removing dead air", "Trim silence or filler from the start/end of a recording before publishing."),
            ("Making a ringtone", "Cut the exact hook or moment you want out of a song for a custom ringtone."),
            ("Extracting a soundbite", "Pull just the relevant few seconds out of a longer interview or recording."),
            ("Splitting a long file", "Break a long recording into two parts for separate editing or upload-size limits."),
            ("Cleaning up voice memos", "Cut a recording down to just the useful part before sharing it."),
        ],
        "tips": [
            "The duration shown is read directly from your uploaded file — if it looks wrong, the file may be corrupted or partially uploaded.",
            "For splitting a file into more than two parts, split once, then split one of the resulting halves again.",
            "Trim before you convert format, not after — it's one less step and keeps quality consistent.",
        ],
        "faq": [
            ("Can I split into more than 2 parts in one pass?", "Not in a single run — split repeatedly on the resulting files for more than two parts."),
            ("What file size limit applies?", "15MB max, same as the other short-audio tools."),
            ("Does trimming lose quality?", "For lossy formats there's a small re-encode; for WAV, trimming is lossless."),
        ],
        "related_tools": ["merge-audio-files", "convert-audio-format", "remove-background-noise"],
        "blog_keywords": ["trim", "cut", "split"],
    },
    "remove-background-noise": {
        "widget": "denoise",
        "usage_key": "denoise",
        "title": "Remove Background Noise Online — Free | VoxCraft",
        "meta_description": "Remove background noise, hiss, and hum from audio online free. Spectral denoise or Studio AI enhancement (Pro).",
        "eyebrow": "Noise Reduction",
        "h1": "Remove background noise from audio online — free",
        "sub": "Standard spectral noise reduction with a strength slider, or Studio AI speech enhancement (Pro) for a real model-based clean-up pass.",
        "intro": [
            'Remove background noise from audio online for free with VoxCraft. Upload a recording, choose Standard or Studio (AI) mode, and download a cleaner version in seconds — no account required. Standard mode uses spectral noise reduction to pull down steady background noise (fan hum, room tone, AC, light hiss) while keeping speech intact.',
            'Studio mode (Pro/Pro+) runs DeepFilterNet, a deep-learning speech-enhancement model in the same class of approach as tools like Adobe Podcast Enhance. Instead of only subtracting a noise profile from the spectrum, it reconstructs what the speech should sound like — which helps on roomy, low-quality, or non-stationary recordings that a simple noise gate cannot fix.',
            'Most free “noise reducers” only offer one spectral pass. VoxCraft pairs a free Standard path with an optional AI Studio path so you can match the tool to the recording: steady hum vs messy real-world speech. For creator workflows, denoise often sits between capture and publish — after you <a href="/tools/extract-audio-from-video" style="color:var(--brass-hi)">extract audio from video</a>, before you <a href="/tools/transcribe-audio-to-text" style="color:var(--brass-hi)">transcribe</a>, or before you normalize loudness for YouTube.',
            'In practice, “remove background noise” is not the same job as “make any bad recording perfect.” Sudden claps, overlapping talk, and heavy music beds need different tools. Use this page when the problem is continuous background energy under a main voice — the most common case for podcasts, voice memos, and interview mics.',
        ],
        "how_it_works": [
            "Upload your recording (15MB max — output is mono).",
            "Choose Standard (fast, free) or Studio (AI enhancement, Pro/Pro+).",
            "In Standard mode, set the strength slider — higher removes more noise but can start to affect speech quality.",
            "Tap Remove noise and listen to the result before downloading.",
        ],
        "use_cases": [
            ("Podcast cleanup", "Reduce a constant room hum picked up by an entry-level microphone — or run Studio mode for a genuinely polished, publish-ready pass."),
            ("Voice memos", "Clean up recordings made in noisy environments like a car or café."),
            ("Interview audio", "Pull down background hiss before transcribing or publishing."),
            ("Pre-transcription cleanup", "Denoise before running through the <a href=\"{transcribe_url}\" style=\"color:var(--brass-hi)\">Transcribe tool</a> to improve accuracy on noisy source audio."),
        ],
        "tips": [
            'Start around 0.4–0.5 strength in Standard mode and increase only if noise is still obvious — aggressive settings can make voices sound thin or watery.',
            'Standard mode targets steady noise (hum, hiss, fan). Studio mode handles a wider range of degradation because it models speech, not only a noise floor.',
            'Studio mode is limited to about 6 minutes per file (AI pass cost/time). For longer files, use Standard or split with the <a href="/tools/trim-cut-audio" style="color:var(--brass-hi)">trim/cut tool</a> first.',
            'Denoise before converting to a heavily compressed MP3 when possible — lossy encode-after-clean usually sounds cleaner than clean-after-encode.',
            'If the file is stereo music with vocals, expect different results than mono speech; this tool is optimized for spoken-word cleanup.',
            'After denoise, check loudness with <a href="/tools/normalize-audio-volume" style="color:var(--brass-hi)">Normalize</a> if you are preparing a podcast or YouTube upload.',
        ],
        "faq": [
            ('What is the difference between Standard and Studio mode?', 'Standard is spectral noise reduction — fast, free, strong on steady hum and hiss. Studio (Pro/Pro+) runs an AI speech-enhancement model that reconstructs speech and can help when the room or mic quality is poor, not only when the noise is a flat hum.'),
            ('Is this free?', 'Standard mode is free to use within the site’s current free-tier limits and does not require an account. Studio AI mode is available on Pro/Pro+ plans. See <a href="/pricing" style="color:var(--brass-hi)">pricing</a> for current limits.'),
            ('Can it remove sudden noises like coughs or door slams?', 'Standard mode is built for continuous background noise, not isolated transients. Studio mode can improve overall speech clarity on messy recordings, but it is not a dedicated “de-click” editor for single events.'),
            ('How does this compare to Adobe Podcast Enhance?', 'Both Studio-style tools use AI speech enhancement rather than a simple EQ. Adobe’s product is polished and account-based. VoxCraft’s free Standard path needs no signup; Studio mode offers a similar class of AI cleanup for eligible plans, plus you stay in the same toolkit for convert, trim, and transcribe.'),
            ('What file types and size limits apply?', 'Typical uploads include common speech formats (for example MP3, WAV, M4A) up to the tool’s current size limit (15MB max on free tools — check the uploader for the live limit). Output is optimized for speech cleanup workflows.'),
            ('Should I denoise before or after transcription?', 'For noisy sources, denoise first, then run <a href="/tools/transcribe-audio-to-text" style="color:var(--brass-hi)">transcribe</a>. Cleaner speech usually improves word error rate, especially on Urdu/Hindi or accented English.'),
            ('Will it damage music or sound effects?', 'Speech-oriented denoisers can dull music and ambiences. Prefer this tool for voice-first files. For music masters, use a dedicated audio editor.'),
            ('Is my audio stored?', 'Processing is for generating your download. See the <a href="/privacy" style="color:var(--brass-hi)">privacy policy</a> for retention details for uploads.'),
        ],
        "related_tools": ["transcribe-audio-to-text", "voice-changer", "convert-audio-format"],
        "blog_keywords": ["noise", "denoise", "clean", "ai enhancement", "deepfilternet"],
    },
    "voice-changer": {
        "widget": "voicechange",
        "usage_key": "voicechange",
        "title": "Voice Changer Online Free — Pitch Effects | VoxCraft",
        "meta_description": "Free online voice changer and pitch changer. Apply pitch shift, robot, echo, chipmunk or deep voice effects to any audio clip. No install, no signup.",
        "eyebrow": "Voice Effects",
        "h1": "Voice changer online — free pitch & effects",
        "sub": "Pitch shift, robot, echo, chipmunk or deep voice — five effects with adjustable parameters.",
        "intro": [
            "Change voice online for free with VoxCraft. Apply pitch shift, chipmunk, deep voice and other effects to a recording in the browser — no account required on the free tier. The Voice Changer applies a deliberate effect rather than trying to make speech sound more natural. Pitch Shift changes pitch while keeping speaking speed the same, which is different from Chipmunk and Deep Voice, which intentionally change both pitch and speed together for a more exaggerated character effect. Robot and Echo layer processing effects on top of the original voice.",
        ],
        "how_it_works": [
            "Upload a voice clip (WAV, MP3, OGG or M4A, 15MB max).",
            "Pick an effect: Pitch Shift, Robot, Echo, Chipmunk, or Deep Voice.",
            "Adjust the effect's specific controls (semitones, intensity, delay/decay).",
            "Tap Apply effect and preview before downloading.",
        ],
        "use_cases": [
            ("Content creators", "Add a character voice for a skit, animation, or narration bit without hiring voice talent."),
            ("Anonymizing a voice", "Pitch-shift a recording where the speaker's identity should be obscured for privacy."),
            ("Sound design", "Use Echo or Robot for stylized effects in a video or audio project."),
            ("Fun/social content", "Chipmunk and Deep Voice are popular for short-form comedic clips."),
        ],
        "tips": [
            "Pitch Shift preserves natural speaking rhythm — use it when you want a different-sounding voice that still sounds human.",
            "Chipmunk/Deep Voice change speed too, so timing relative to any video will shift — account for that if syncing to picture.",
            "Echo's decay controls how quickly repeats fade — lower decay values sound subtler.",
        ],
        "faq": [
            ("Can I clone a specific person's voice with this?", "No — this tool applies effects to your uploaded audio. For AI voice cloning from a reference sample, see VoxCraft's <a href=\"{voiceclone_url}\" style=\"color:var(--brass-hi)\">voice cloning</a> page (Pro+)."),
            ("What's the semitone range?", "±12 semitones (one full octave up or down) on Pitch Shift."),
            ("Does this work on music, not just speech?", "It's tuned for voice, but you can experiment with other audio — results vary."),
        ],
        "related_tools": ["remove-background-noise", "ai-music-generator", "convert-audio-format"],
        "blog_keywords": ["voice effect", "pitch", "robot voice"],
    },
    "extract-audio-from-video": {
        "widget": "videoxtract",
        "usage_key": "videoxtract",
        "title": "Extract Audio from Video Online Free | VoxCraft",
        "meta_description": "Free online audio extractor. Convert MP4, MOV, MKV or WEBM to MP3 or WAV in your browser. No signup required.",
        "eyebrow": "Video → Audio",
        "h1": "Extract audio from video online — free",
        "sub": "Pull the soundtrack out of MP4, AVI, MOV, MKV or WEBM — up to 50MB, since video files run larger.",
        "intro": [
            'Extract audio from video online for free with VoxCraft. Upload an MP4, MOV, WebM or similar file and download the audio track as MP3 or WAV — no install, no account required on the free tier.',
            'Creators use extraction when the video is only a container: screen recordings, camera interviews, Zoom exports, or phone clips where the picture is secondary. Once you have a clean audio file, you can denoise, transcribe, convert, or drop it into a podcast timeline without opening a full video editor.',
            'Unlike desktop suites, this page is a single-purpose browser tool: separate the soundtrack, choose a practical format, download. Typical next steps on VoxCraft are <a href="/tools/remove-background-noise" style="color:var(--brass-hi)">noise reduction</a>, <a href="/tools/transcribe-audio-to-text" style="color:var(--brass-hi)">transcription</a>, or <a href="/tools/convert-audio-format" style="color:var(--brass-hi)">format conversion</a>.',
            'Respect copyright and platform rules: extract audio only from video you own or have rights to use. “Online MP4 to MP3” tools are often used for legitimate editing workflows, not for stripping commercial music from other people’s uploads.',
        ],
        "how_it_works": [
            "Upload your video (MP4, AVI, MOV, MKV or WEBM, up to 50MB).",
            "Choose an output format (MP3, WAV or OGG) and bitrate.",
            "Tap Extract audio and wait — larger files take longer.",
            "Download the resulting audio-only file.",
        ],
        "use_cases": [
            ("Podcast from video", "Extract audio from a recorded video interview to publish as a podcast episode."),
            ("Reusing narration", "Pull voiceover out of an old video project to reuse or edit separately."),
            ("Transcription prep", "Extract the audio track, then run it through <a href=\"{transcribe_url}\" style=\"color:var(--brass-hi)\">Transcribe</a> for a text version of a video's dialogue."),
            ("Music/sample extraction", "Get the audio from a video clip for further editing or sampling (where you have the rights to do so)."),
        ],
        "tips": [
            'Prefer WAV if you will denoise or edit further; use MP3 for smaller sharing files.',
            'If the video is huge, trim it in a video app first or expect longer upload times.',
            'After extract, normalize loudness before publishing if levels are uneven.',
            'For multi-track professional projects, a NLE still wins — this tool is for fast single-track extraction.',
        ],
        "faq": [
            ('Is extracting audio from video free?', 'Yes on the free tier within current limits, without required signup.'),
            ('What video formats work?', 'Common containers such as MP4, MOV, and WebM are typical. If a file fails, convert the video in another tool or re-export from the original app.'),
            ('MP3 or WAV — which should I pick?', 'WAV for further editing/denoise; MP3 for smaller distribution files.'),
            ('Can I extract only part of the timeline?', 'This tool focuses on the full audio track. For a section, extract first then <a href="/tools/trim-cut-audio" style="color:var(--brass-hi)">trim</a>, or cut the video before upload.'),
            ('Will this separate speakers or music beds?', 'No. It extracts the mixed audio track as recorded, not stem separation.'),
            ('Is this legal for any YouTube URL?', 'Do not use extraction to infringe copyright. Work with files you own or are licensed to process.'),
            ('What is a typical creator workflow?', 'Extract → optional denoise → transcribe or edit → publish. See also <a href="/audio-tools-for-youtubers" style="color:var(--brass-hi)">audio tools for YouTubers</a>.'),
        ],
        "related_tools": ["convert-audio-format", "trim-cut-audio", "transcribe-audio-to-text"],
        "blog_keywords": ["video", "extract", "screen recording"],
    },
    "ai-music-generator": {
        "widget": "music",
        "usage_key": None,
        "title": "AI Music Generator Free — Text to Music | VoxCraft",
        "meta_description": "Generate original AI music from a text prompt online. Instrumentals or songs with vocals — Pro+ feature.",
        "eyebrow": "AI Music",
        "h1": "AI music generator — text to music online",
        "sub": "Describe genre, mood and instruments as tags; get a real instrumental or vocal track back. Pro+ feature powered by ACE-Step.",
        "intro": [
            "Generate AI music online with VoxCraft’s text-to-music tool. Describe the style you want as comma-separated tags (genre, mood, instruments, tempo), optionally add structured lyrics, and get back an original track between 10 and 120 seconds — powered by ACE-Step (Apache 2.0). Always double-check current licensing details before publishing commercially.",
            "Unlike stock libraries where every channel ends up with the same beds, text-to-music lets you match a specific mood in one pass. A lofi piano loop for a study video, a short upbeat sting for a podcast intro, or a cinematic bed under a faceless explainer — all from a short prompt instead of searching license pages.",
            "This page is the dedicated AI music generator workflow inside VoxCraft. It sits next to text-to-speech, voice cloning, and free audio tools (trim, denoise, normalize, merge, convert) so you can generate a bed and then clean or combine it without leaving the site. Generation is a Pro+ feature because each run uses a GPU worker; see pricing for current monthly track limits.",
            "Practical path: write 4–8 specific tags → choose instrumental or add [verse]/[chorus] lyrics → set duration (start short for tests) → generate → preview on phone speakers → download WAV → optionally send to Trim, Denoise or Normalize. For commercial releases, keep a note of the prompt and date and re-check ACE-Step / VoxCraft terms before a big publish.",
        ],
        "how_it_works": [
            "Enter style tags in plain language — e.g. “lofi, chill, piano, soft drums, 90 bpm, warm, night.” Specific tags beat vague ones.",
            "Leave Instrumental checked for a music bed, or uncheck it and paste lyrics structured with [verse], [chorus], and [bridge] so the model can follow song form.",
            "Set duration between 10 and 120 seconds. Shorter clips (10–30s) are faster and usually enough for intros, transitions, and Shorts.",
            "Tap Generate track. Warm runs often finish in about a minute; the first request after idle can take several minutes while the GPU worker loads models.",
            "When status shows Done, preview in the player, download the WAV, and optionally open Trim, Denoise, Normalize or Merge to finish the edit.",
        ],
        "use_cases": [
            ("YouTube background music", "Generate a mood-matched instrumental bed for faceless, tutorial, or explainer videos without recycling the same stock loops every other channel uses."),
            ("Podcast intros and outros", "Create a short, distinctive musical sting or bed for show branding, then trim and normalize it for consistent loudness."),
            ("Shorts, Reels and TikTok", "Produce 10–30 second instrumental beds that fit vertical video pacing; regenerate quickly when the edit changes."),
            ("Prototyping and temp scores", "Test genre/mood combinations before committing to a paid composer or a larger stock license — useful for client drafts and pitch videos."),
            ("Course and product videos", "Add simple, consistent beds under lesson narration or product demos so the voice stays primary and the music stays in the background."),
            ("Game and app mockups", "Generate temporary loops for prototype builds or marketing clips while final audio is still in progress."),
        ],
        "tips": [
            "Prefer concrete tags over vague mood words alone. “lofi, chill, piano, soft drums, 90 bpm, warm” steers the model better than only “chill music.”",
            "For vocal tracks, structure lyrics with [verse], [chorus], and [bridge]. Clear section tags help the model keep form instead of drifting.",
            "Start with 15–30 second tests. Short runs cost less GPU time, fail faster when a prompt is wrong, and are often enough for intros and social clips.",
            "If a track feels too busy under speech, regenerate with fewer instruments or words like “sparse,” “minimal,” or “soft pad only,” then lower the bed in your editor.",
            "After download, use Normalize (streaming/podcast presets) or Adjust Volume so the bed sits under narration instead of competing with it.",
            "Cold starts after the worker scales to zero can take several minutes the first time. Leave the tab open; status updates automatically. Subsequent generations on a warm worker are much faster.",
        ],
        "faq": [
            ("Is the AI music generator free?", "No. AI music generation is a Pro+ feature because each track runs on a GPU worker. Free users can still use text-to-speech and the free audio tools. See <a href=\"/pricing\" style=\"color:var(--brass-hi)\">pricing</a> for current plans and monthly track limits."),
            ("Can I use generated tracks commercially?", "ACE-Step is Apache 2.0 licensed, which is generally commercial-friendly for the model output. Always confirm current ACE-Step terms and VoxCraft Terms before relying on a track for a paid release, ad, or client deliverable."),
            ("How long does generation take?", "On a warm worker, many tracks finish in roughly 30–90 seconds depending on duration and load. The first request after the worker has scaled to zero (cold start) can take several minutes while models load. Leave the page open; the status poll continues until done or error."),
            ("Why did generation time out or never finish?", "Long waits usually mean a cold GPU start or a temporary worker issue. Wait up to about 10–12 minutes on the first try after idle. If status still shows generating or returns a timeout error, try again — the next run is often much faster once the container is warm."),
            ("Instrumental vs vocals — how do I choose?", "Keep Instrumental checked for background beds under voiceover. Uncheck it and supply lyrics when you want a sung track. Use [verse], [chorus], and [bridge] tags so structure stays clear."),
            ("What duration should I use?", "10–30 seconds for intros, outros, transitions, and Shorts. 45–90 seconds for longer beds under sections of a video. Max is 120 seconds per generation."),
            ("What format do I get?", "Downloads are WAV for maximum compatibility with editors. Convert to MP3 or other formats with the free <a href=\"/tools/convert-audio-format\" style=\"color:var(--brass-hi)\">Convert audio format</a> tool if a platform requires it."),
            ("How is this different from stock music sites?", "You describe a style once and get a new take instead of browsing the same popular loops. Results vary by prompt; treat strong takes as drafts you can trim and level with the other VoxCraft tools."),
            ("Does this separate stems (drums, vocals, bass)?", "No. You get a mixed track. For speech cleanup under music, use denoise/normalize tools on voice tracks separately rather than expecting stem separation here."),
            ("Is there a limit on how many tracks I can make?", "Yes. Pro+ accounts have a monthly music generation quota shown in the product UI and on the pricing page. Limits exist so GPU cost stays sustainable."),
        ],
        "related_tools": ["voice-changer", "merge-audio-files", "convert-audio-format", "normalize-audio-volume", "trim-cut-audio"],
        "blog_keywords": ["music", "ace-step", "generate", "ai music", "text to music"],
    },

    "normalize-audio-volume": {
        "widget": "normalize",
        "usage_key": "normalize",
        "title": "Normalize Audio Volume Online Free | VoxCraft",
        "meta_description": "Normalize audio volume online free. LUFS (EBU R128) with Spotify, YouTube, and podcast presets.",
        "eyebrow": "Normalize",
        "h1": "Normalize audio volume online — free",
        "sub": "Bring quiet clips up and tame loud peaks — quick peak normalize, or true LUFS loudness matching to a streaming, podcast or broadcast target.",
        "intro": [
            "Normalize audio volume online for free with VoxCraft. Level a clip with peak normalize or true loudness (LUFS) so it matches streaming and podcast targets — no account required. Peak normalize is the fast option: gain is set so the loudest sample reaches a target dBFS. LUFS mode measures perceived loudness per ITU-R BS.1770 / EBU R128 — the same standard Spotify, YouTube and podcast platforms use to decide whether to turn your upload up or down — and matches it to a target so two files with different dynamics still sound equally loud.",
            "Unlike a simple volume slider, both modes analyze the file and calculate the right gain automatically rather than asking you to guess.",
        ],
        "how_it_works": [
            "Upload an audio file (15MB max).",
            "Choose Peak (default −3 dBFS is safe for most platforms) or LUFS mode.",
            "In LUFS mode, pick a preset — Streaming (−14), Podcast (−16), Broadcast (−23) — or set a custom target.",
            "Tap Normalize and download the result.",
        ],
        "use_cases": [
            ("Podcast edits", "Match level across takes recorded on different days or mics, or hit a platform's loudness guidance with LUFS mode."),
            ("YouTube voiceover", "Avoid a quiet narration track against music beds; LUFS mode targets the −14 LUFS streaming platforms actually expect."),
            ("Before merge", "Normalize each clip first so joins don't jump in loudness."),
            ("Meeting platform loudness targets", "Use the Streaming, Podcast or Broadcast preset instead of guessing a peak dB value."),
        ],
        "tips": [
            "−3 dBFS is a safe peak-mode default for web and social uploads.",
            "If you're publishing to Spotify, YouTube or a podcast platform, LUFS mode with the matching preset gets you closer to their target than peak normalize ever can.",
            "If a file is already very loud, normalize will reduce it rather than boost into clipping.",
            "For a fixed boost or cut in dB, use the Adjust Volume tool instead.",
        ],
        "faq": [
            ("What's the difference between Peak and LUFS mode?", "Peak normalize sets gain so the loudest sample hits a target dBFS — fast, but two files with different dynamics can still sound different in loudness. LUFS mode measures true perceived loudness (ITU-R BS.1770 / EBU R128) and matches it to a target, which is what streaming and podcast platforms actually check."),
            ("Which LUFS target should I use?", "−14 LUFS for Spotify/YouTube/streaming, −16 LUFS is common podcast-platform guidance, −23 LUFS (EBU R128) for broadcast. Pick the preset that matches where you're publishing."),
            ("Will it clip?", "No — both modes true-peak-limit before export rather than letting gain push past 0 dBFS."),
        ],
        "related_tools": ["adjust-audio-volume", "merge-audio-files", "convert-audio-format"],
        "blog_keywords": ["normalize", "volume", "loudness", "lufs"],
    },
    "adjust-audio-volume": {
        "widget": "volume",
        "usage_key": "volume",
        "title": "Adjust Audio Volume Online Free — Gain Control | VoxCraft",
        "meta_description": "Adjust audio volume online free. Boost or lower gain by a fixed dB amount. Simple volume control for voiceovers and beds.",
        "eyebrow": "Volume",
        "h1": "Adjust audio volume online — free",
        "sub": "Raise or lower an entire clip by a fixed amount in decibels.",
        "intro": [
            "Adjust audio volume online for free with VoxCraft. Raise or lower gain by a fixed amount when you already know you want about +3 dB more or need to turn a bed down — no install required. For automatic leveling across files, prefer the Normalize tool.",
        ],
        "how_it_works": [
            "Upload your file.",
            "Set gain from −12 dB to +12 dB.",
            "Apply and download.",
        ],
        "use_cases": [
            ("Music under voice", "Drop a bed a few dB so narration stays clear."),
            ("Quiet phone memo", "Add a small boost before editing."),
        ],
        "tips": [
            "Large boosts can clip — if the result distorts, try a smaller gain or Normalize instead.",
            "After adjusting, you can still run Normalize for a consistent peak.",
        ],
        "faq": [
            ("What's the difference vs Normalize?", "Volume applies a fixed dB change. Normalize measures the peak and chooses the gain for you."),
        ],
        "related_tools": ["normalize-audio-volume", "fade-audio", "merge-audio-files"],
        "blog_keywords": ["volume", "gain", "boost"],
    },
    "change-audio-speed": {
        "widget": "speed",
        "usage_key": "speed",
        "title": "Audio Speed Changer Online Free | VoxCraft",
        "meta_description": "Speed up or slow down audio online free (0.5×–2×). Keep pitch or allow shift. Perfect for Shorts, voice memos and practice.",
        "eyebrow": "Speed",
        "h1": "Change audio speed online — free",
        "sub": "Make a clip faster or slower in your browser — 0.5× to 2×.",
        "intro": [
            "Change audio speed online for free with VoxCraft. Speed up or slow down a clip while optionally preserving pitch — ideal for voiceovers and Shorts. Speeding up shortens duration; slowing down stretches it. By default pitch is preserved (time-stretch), so speech still sounds like the same person.",
        ],
        "how_it_works": [
            "Upload an audio file (15MB max).",
            "Pick a speed (or use presets like 1.25×).",
            "Download the result.",
        ],
        "use_cases": [
            ("YouTube Shorts", "Tighten a voiceover that runs a few seconds too long."),
            ("Practice", "Slow a phrase to learn pronunciation."),
            ("Podcasts", "Slightly speed long reads without a full re-record."),
        ],
        "tips": [
            "1.25× is a common sweet spot for spoken content.",
            "Extreme speeds (near 0.5× or 2×) sound more artificial — preview before publishing.",
            "If you need pitch locked while changing speed, that requires a dedicated time-stretch tool (not included here).",
        ],
        "faq": [
            ("Does pitch stay the same?", "Yes by default — time-stretch keeps pitch. Uncheck “Keep original pitch” only if you want the classic chipmunk/slow effect."),
            ("Max speed?", "2× faster or 0.5× slower."),
        ],
        "related_tools": ["trim-cut-audio", "convert-audio-format", "voice-changer"],
        "blog_keywords": ["speed", "tempo", "speed up"],
    },
    "fade-audio": {
        "widget": "fade",
        "usage_key": "fade",
        "title": "Fade In Fade Out Audio Online Free | VoxCraft",
        "meta_description": "Add fade in and fade out to audio online free. Smooth starts and ends on MP3 or WAV before merging or publishing to YouTube.",
        "eyebrow": "Fade",
        "h1": "Fade in fade out audio online — free",
        "sub": "Smooth the start and end of a clip so it doesn't click in a video or merge.",
        "intro": [
            "Add fade in and fade out to audio online for free with VoxCraft. Soften hard starts and stops before you publish a video or podcast — one of the easiest polish steps, no editor install required.",
        ],
        "how_it_works": [
            "Upload your clip.",
            "Set fade-in and fade-out in milliseconds.",
            "Apply and download.",
        ],
        "use_cases": [
            ("Video voiceover", "Soft start so the first word isn't abrupt."),
            ("Music beds", "Fade out under the last line of narration."),
            ("Before merge", "Fade edges so joins feel cleaner."),
        ],
        "tips": [
            "300–800 ms is enough for most voice clips.",
            "Very long fades on short clips will swallow content — keep fades shorter than half the duration.",
        ],
        "faq": [
            ("Can I fade only one side?", "Yes — set the other side to 0 ms."),
        ],
        "related_tools": ["merge-audio-files", "trim-cut-audio", "normalize-audio-volume"],
        "blog_keywords": ["fade", "fade in", "fade out"],
    },
    "split-audio-by-silence": {
        "widget": "split",
        "usage_key": "split",
        "title": "Split Audio by Silence Online Free | VoxCraft",
        "meta_description": "Split audio by silence online free. Auto-cut long recordings into separate clips at pauses. Ideal for interviews and multi-take voiceovers.",
        "eyebrow": "Split",
        "h1": "Split audio by silence online — free",
        "sub": "Cut a long file into separate parts wherever there's a pause.",
        "intro": [
            "Split audio by silence online for free with VoxCraft. Automatically cut a long recording into separate clips at quiet gaps — useful when you've recorded several takes in one file or an interview with natural pauses.",
        ],
        "how_it_works": [
            "Upload a recording (15MB max).",
            "Set how long a pause must be to count as a split, and how quiet “silence” is.",
            "Tap Split — download each part individually (up to 20 parts).",
        ],
        "use_cases": [
            ("Multi-take VO", "Record five takes, split, keep the best."),
            ("Interviews", "Break a long conversation into topic chunks."),
            ("Podcasts", "Separate segments before editing."),
        ],
        "tips": [
            "If you get too many tiny clips, raise Min silence (e.g. 800–1200 ms).",
            "If it won't split, lower the silence threshold (more negative = treats more of the file as sound).",
            "Room noise can prevent clean splits — denoise first if needed.",
        ],
        "faq": [
            ("What's the part limit?", "20 parts per run so the page stays responsive."),
            ("Can I merge them again?", "Yes — use Merge after you delete the takes you don't want."),
        ],
        "related_tools": ["trim-cut-audio", "merge-audio-files", "remove-background-noise"],
        "blog_keywords": ["split", "silence", "chapters"],
    },
    "reverse-audio": {
        "widget": "reverse",
        "usage_key": "reverse",
        "title": "Audio Reverser Online Free — Reverse Clip | VoxCraft",
        "meta_description": "Free online audio reverser. Play any MP3 or WAV backwards in your browser. Instant reverse for effects, transitions and hidden messages.",
        "eyebrow": "Reverse",
        "h1": "Reverse audio online — free",
        "sub": "Play a clip backwards in one click.",
        "intro": ["Reverse audio online for free with VoxCraft. Flip a clip backwards for effects, transitions, or a quick reverse check — simple, fast, and browser-based."],
        "how_it_works": ["Upload a file (15MB max).", "Tap Reverse.", "Download the result."],
        "use_cases": [("Effects", "Create reverse reverb tails or transition stingers."), ("Checking edits", "Spot issues by hearing material backwards.")],
        "tips": ["Works on any mono or stereo clip under the size limit."],
        "faq": [("Does it change pitch?", "No — it only reverses time order.")],
        "related_tools": ["change-audio-speed", "fade-audio", "convert-audio-format"],
        "blog_keywords": ["reverse"],
    },
    "stereo-to-mono": {
        "widget": "mono",
        "usage_key": "mono",
        "title": "Convert Stereo to Mono Online Free | VoxCraft",
        "meta_description": "Convert stereo to mono online free. Collapse left and right channels into one mono file for voiceovers and smaller uploads.",
        "eyebrow": "Mono",
        "h1": "Stereo to mono converter online — free",
        "sub": "Collapse left and right into one mono channel.",
        "intro": ["Convert stereo to mono online for free with VoxCraft. Collapse a stereo file to mono for voice-only uploads, phone playback, and smaller file sizes — no install required."],
        "how_it_works": ["Upload a stereo file.", "Tap Convert to mono.", "Download."],
        "use_cases": [("Voiceover", "Simplify a dual-channel VO to mono."), ("Compatibility", "Some platforms prefer mono speech.")],
        "tips": ["If one side is silent, mono still keeps the active side."],
        "faq": [("Is quality lost?", "You combine channels; peak levels are preserved as much as possible.")],
        "related_tools": ["convert-audio-format", "normalize-audio-volume", "trim-cut-audio"],
        "blog_keywords": ["mono", "stereo"],
    },
    "loop-audio": {
        "widget": "loop",
        "usage_key": "loop",
        "title": "Loop Audio Online Free — Repeat a Clip | VoxCraft",
        "meta_description": "Loop audio online free. Repeat any clip 2–10 times for music beds, intros and stingers. No install required.",
        "eyebrow": "Loop",
        "h1": "Loop audio online — free",
        "sub": "Repeat a short clip two to ten times.",
        "intro": ["Loop audio online for free with VoxCraft. Repeat a short bed or stinger to cover a longer section without opening a full DAW — browser-based and free to try."],
        "how_it_works": ["Upload a short clip.", "Choose how many repeats (2–10).", "Download the looped file."],
        "use_cases": [("Music beds", "Extend a short instrumental under a longer VO."), ("Intros", "Repeat a sting for a longer bumper.")],
        "tips": ["For seamless music loops, start with a clip that already ends cleanly on a beat."],
        "faq": [("Max repeats?", "10, to keep files manageable.")],
        "related_tools": ["fade-audio", "merge-audio-files", "change-audio-speed"],
        "blog_keywords": ["loop", "repeat"],
    },
    "simple-audio-eq": {
        "widget": "eq",
        "usage_key": "eq",
        "title": "Simple Audio EQ Online Free — Bass & Treble | VoxCraft",
        "meta_description": "Online audio EQ free. Boost or cut bass and treble for clearer voiceovers and warmer music beds. Two-band EQ, no install.",
        "eyebrow": "EQ",
        "h1": "Simple audio EQ online — free",
        "sub": "Adjust bass and treble with two controls.",
        "intro": ["Apply a simple audio EQ online for free with VoxCraft. Use a light two-band EQ for quick bass/treble fixes — not a replacement for a full studio parametric EQ, but fast for everyday polish."],
        "how_it_works": ["Upload audio.", "Move Bass and Treble sliders.", "Apply and download."],
        "use_cases": [("Voice clarity", "Add a little treble so speech cuts through."), ("Warmth", "Add a touch of bass on thin recordings.")],
        "tips": ["Small moves (±3 dB) are usually enough. Large boosts can muddy or hiss."],
        "faq": [("Is this a full EQ?", "No — two shelves only. Enough for quick creator polish.")],
        "related_tools": ["normalize-audio-volume", "remove-background-noise", "convert-audio-format"],
        "blog_keywords": ["eq", "bass", "treble"],
    },
    "video-audio-redub": {
        "widget": "redub",
        "usage_key": None,  # Pro-only; no free daily counter
        "title": "AI Dubbing & Video Redub Online Free | VoxCraft",
        "meta_description": "Redub video online. Translate and replace spoken audio in 40+ languages with neural AI voices. AI video dubbing for creators.",
        "eyebrow": "Video redub",
        "h1": "Video redub online — AI translate & re-voice",
        "sub": "Upload a video, pick a target language and voice, get a new dubbed track muxed back onto the original picture. Pro plan.",
        "intro": [
            "Redub video audio online with VoxCraft. Keep the original picture and replace the spoken track: extract audio, transcribe, translate, re-voice with a neural voice, then mux back onto the video — without needing a cloned voice or local GPU.",
            "This is the practical path for creators who want an Urdu, Hindi, Tamil, or English version of an existing clip without re-recording. Phase 1 uses the same neural voices as Studio; voice-cloning the original speaker is a later option under Pro+.",
        ],
        "how_it_works": [
            "Upload an MP4/MOV/WebM/MKV (up to 50MB, up to ~10 minutes).",
            "Choose the source language for transcription (or leave Auto).",
            "Pick the target language and any of the 130+ stock voices — same picker as Studio.",
            "VoxCraft transcribes, translates with Google NMT, generates the new voice with edge-tts, and muxes it onto your video.",
            "Download the dubbed MP4, or just the new audio track if you prefer to re-mux yourself.",
        ],
        "use_cases": [
            ("YouTube localization", "Ship the same explainer in Urdu and Hindi without re-recording the VO."),
            ("Course modules", "Turn one English lesson video into region-specific versions for students."),
            ("Shorts / Reels", "Repurpose a viral clip into another language while keeping the original edit."),
            ("Client delivery", "Provide a dubbed cut when the client needs a second language track quickly."),
        ],
        "tips": [
            "Clear speech transcribes better than music-heavy or noisy tracks — denoise first if needed.",
            "If source and target are the same language, translation is skipped and only the voice is replaced.",
            "Match the target voice's language to the target language for natural pronunciation.",
            "Long videos burn TTS character quota the same way Studio does — a 5-minute script is typically a few thousand characters.",
        ],
        "faq": [
            ("Is this free?", "No — redub is included with the Pro plan. Free accounts can still use Transcribe and Extract audio separately."),
            ("Does it clone the original speaker?", "Not in Phase 1. It uses the same stock neural voices as Studio (130+ voices, 40+ languages). Cloned-speaker redub is a later Pro+ option."),
            ("Which languages work?", "Any language pair where we have a stock voice and Google Translate coverage — including Urdu, Hindi, Bengali, Punjabi, Tamil, Telugu, Arabic, and English variants."),
            ("What happens to the original audio?", "It is replaced. Download the separate audio track if you want both."),
            ("How long can a video be?", "Up to about 10 minutes and 50MB in Phase 1."),
        ],
        "related_tools": ["transcribe-audio-to-text", "extract-audio-from-video", "convert-audio-format"],
        "blog_keywords": ["redub", "dubbing", "translate video", "video voiceover"],
    },
}

TOOL_ORDER = [
    "transcribe-audio-to-text", "convert-audio-format", "compress-audio", "decompress-audio",
    "merge-audio-files", "trim-cut-audio",
    "remove-background-noise", "normalize-audio-volume", "adjust-audio-volume", "change-audio-speed",
    "fade-audio", "split-audio-by-silence", "reverse-audio", "stereo-to-mono", "loop-audio",
    "simple-audio-eq", "voice-changer", "extract-audio-from-video", "video-audio-redub", "ai-music-generator",
]


# Fields the admin form is allowed to override. Structural keys (widget,
# usage_key, related_tools, blog_keywords) stay in code so a bad form
# save cannot break routing or the widget include.
EDITABLE_TOOL_FIELDS = (
    "title", "meta_description", "eyebrow", "h1", "sub",
    "intro", "how_it_works", "use_cases", "tips", "faq",
)


def _load_synced_overrides() -> dict:
    """Load data/page_content_overrides.json, written by the admin panel's
    manual "Push all changes to repo" button (see github_sync.py). Returns
    {} if it doesn't exist yet (nothing has ever been synced) or is
    malformed — either way, TOOL_PAGES below just keeps its hardcoded
    values, same as before this existed."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "page_content_overrides.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


# Bake the last-synced admin content into TOOL_PAGES itself at import time.
# Why: get_tool_page() below merges live DB overrides on top of TOOL_PAGES
# at request time, which is instant but only as durable as the DB. This
# merge instead updates the *code-level baseline* once, at process start,
# so a fresh deploy — even one pointed at a brand new, empty database —
# already shows the last-pushed content instead of silently reverting to
# whatever prose was hardcoded here months ago. The DB (and its own
# overrides) still always wins for anything edited since the last sync.
for _slug, _override in _load_synced_overrides().items():
    if not _slug.startswith("tool:"):
        continue
    _tool_slug = _slug[len("tool:"):]
    _base = TOOL_PAGES.get(_tool_slug)
    if not _base:
        continue
    for _key in EDITABLE_TOOL_FIELDS:
        if _key in _override and _override[_key] is not None:
            _base[_key] = _override[_key]


def get_tool_page(slug: str):
    """Return the effective tool page dict: code defaults merged with any
    admin overrides stored in page_content. Returns None if slug unknown.
    """
    base = TOOL_PAGES.get(slug)
    if not base:
        return None
    try:
        import persistence
        override = persistence.load_page_content(f"tool:{slug}") or {}
    except Exception:
        override = {}
    out = dict(base)
    for key in EDITABLE_TOOL_FIELDS:
        if key in override and override[key] is not None:
            out[key] = override[key]
    return out
