"""
Format- and use-case-specific landing pages for VoxCraft's existing tools.

Why this exists (keyword research, Oct 2026): head terms like "mp3 cutter",
"audio trimmer" or "mp4 to mp3" are owned by sites with millions of monthly
visits, so VoxCraft can't realistically rank for them yet. Narrower queries
-- "opus to mp3" (WhatsApp voice notes), "amr to mp3", "mov to mp3" (iPhone
video), "remove hum from audio", "make a ringtone from an MP3" -- have far
less competition and are exactly what the existing tools already do.

Each entry below reuses an EXISTING widget partial (convert, videoxtract,
transcribe, cutter, denoise), so there is no new backend or UI code to keep
in sync. Every page carries its own written content (what the format is,
when conversion helps, honest limits, FAQ) rather than a swapped-out title
on identical text -- thin near-duplicate pages are exactly what AdSense
rejected the site for before, so don't add an entry here without real,
specific copy.

tool_pages.py merges FORMAT_PAGES into TOOL_PAGES at import, so these pages
are routed at /tools/<slug>, sitemapped, editable in /admin/seo and
cross-linked automatically. They are deliberately NOT in TOOL_ORDER (the
18+ core tools); they appear under "Convert by format" on the /tools hub.

Optional per-page key: "default_format" preselects the output format in the
convert / videoxtract widgets.
"""


def _a(slug: str, text: str) -> str:
    return f"<a href='/tools/{slug}' style='color:var(--brass-hi)'>{text}</a>"


FORMAT_PAGES = {
    # ------------------------------------------------------------------
    # Audio format converters (convert widget)
    # ------------------------------------------------------------------
    "opus-to-mp3": {
        "widget": "convert",
        "usage_key": "convert",
        "default_format": "mp3",
        "title": "Opus to MP3 Converter Online Free — WhatsApp Voice Notes | VoxCraft",
        "meta_description": "Convert Opus to MP3 online free. Turn WhatsApp voice messages (.opus) into MP3 you can play anywhere. No install, no signup.",
        "eyebrow": "Opus → MP3",
        "h1": "Opus to MP3 converter online — free",
        "sub": "Upload an .opus file — such as a WhatsApp voice message — and download it as an MP3 that plays on any phone, laptop or editor.",
        "intro": [
            "Convert Opus to MP3 online for free with VoxCraft. Upload an .opus file, keep MP3 selected, and download a file that opens in practically every player and editing app — no install and no account on the free tier.",
            "Opus is a modern, efficient audio codec that is very good at speech, which is why WhatsApp uses it for voice messages. The catch is compatibility: many video editors, older phones, car stereos and desktop players still don't open .opus files. MP3 is the universal fallback.",
            "If you saved a voice message from WhatsApp and need to send it by email, drop it into a video editor, or keep it as a normal audio file, this is the quickest route. If what you actually need is the words, skip the conversion and use " + _a("whatsapp-voice-note-to-text", "voice note to text") + " instead.",
            "One honest note: Opus to MP3 is a lossy-to-lossy conversion, so nothing is gained in quality — the aim is compatibility. Voice messages are stored at a low bitrate to begin with, so a 128 kbps MP3 is plenty and won't make them sound worse in any way you can hear.",
        ],
        "how_it_works": [
            "Upload your .opus file (15MB max, 20MB with Pro). WhatsApp voice notes are usually well under this.",
            "Leave the output format on MP3. For speech, 128 kbps is a sensible quality setting.",
            "Tap Convert and wait a few seconds.",
            "Download the MP3, or send it straight to another tool such as trim or normalize.",
        ],
        "use_cases": [
            ("WhatsApp voice messages", "Save a voice note as an MP3 you can email, upload to a form, or open on a computer that can't play .opus."),
            ("Video editing", "Convert a voice message to MP3 so it can be dropped onto an editor's timeline."),
            ("Podcast and interview clips", "Turn an Opus recording from a chat or call app into a standard file for your editor."),
        ],
        "tips": [
            "For speech, 96–128 kbps is enough; a higher bitrate makes the file bigger without sounding better.",
            "If the voice note is very quiet, run it through " + _a("normalize-audio-volume", "Normalize") + " after converting.",
            "Long voice notes can be cut down first with the " + _a("trim-cut-audio", "trim tool") + ".",
            "Need WAV for an editor instead? Switch the output to WAV — it is larger but not re-compressed.",
        ],
        "faq": [
            ("What is an .opus file?", "Opus is an open audio codec built for speech and music at low bitrates. WhatsApp voice messages are Opus audio, usually saved with an .opus extension."),
            ("Why won't my .opus file play?", "Support is patchy: some players, editors and older devices don't recognise it. Converting to MP3 solves that."),
            ("Does converting reduce quality?", "Opus to MP3 re-encodes already-compressed audio, so there is a small theoretical loss and no gain. For voice messages the difference is not noticeable at 128 kbps."),
            ("Can I convert Opus to WAV instead?", "Yes — choose WAV as the output format. The file will be much larger but is a good source for editing."),
            ("Is there a file size limit?", "Free accounts can upload up to 15MB per file; Pro allows up to 20MB."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start."),
        ],
        "related_tools": ["convert-audio-format", "whatsapp-voice-note-to-text", "trim-cut-audio", "normalize-audio-volume"],
        "blog_keywords": ["opus", "whatsapp", "voice message", "convert"],
    },
    "amr-to-mp3": {
        "widget": "convert",
        "usage_key": "convert",
        "default_format": "mp3",
        "title": "AMR to MP3 Converter Online Free | VoxCraft",
        "meta_description": "Convert AMR to MP3 online free. Make old phone voice recordings and call recordings playable everywhere. No install, no signup.",
        "eyebrow": "AMR → MP3",
        "h1": "AMR to MP3 converter online — free",
        "sub": "Turn an .amr voice recording from an older phone or call recorder into an MP3 that plays on any device.",
        "intro": [
            "Convert AMR to MP3 online for free with VoxCraft. Upload an .amr file, keep MP3 selected, and download a file that plays in any player or editor — no install and no signup on the free tier.",
            "AMR (Adaptive Multi-Rate) is a speech codec designed for phone calls. Older Android and feature phones, some call-recording apps and a few voice recorders still save .amr files. It produces very small files, but most computers, editors and websites don't open it.",
            "Because AMR was built for telephone speech, the audio is typically narrowband — it sounds like a phone call. Converting to MP3 won't add detail that was never recorded, but it makes the recording usable: you can play it, trim it, clean it up and share it.",
            "A good next step for a muffled recording is " + _a("remove-background-noise", "noise reduction") + " and then " + _a("normalize-audio-volume", "normalize") + " to bring the level up.",
        ],
        "how_it_works": [
            "Upload your .amr file (15MB max, 20MB with Pro).",
            "Leave the output format on MP3. 128 kbps is more than enough for speech this narrow.",
            "Tap Convert and wait a few seconds.",
            "Download the MP3 and open it anywhere.",
        ],
        "use_cases": [
            ("Old phone recordings", "Rescue voice memos and call recordings stored as .amr on an old handset or memory card."),
            ("Evidence and notes", "Make a recording playable on a computer so it can be reviewed, trimmed or transcribed."),
            ("Interviews and lectures", "Convert a lecture recorded on a basic voice recorder into a standard file."),
        ],
        "tips": [
            "AMR audio is low-bandwidth speech; expect it to sound like a phone call even after conversion.",
            "Quiet recordings usually benefit from normalizing after conversion.",
            "Want the words? After converting, run it through " + _a("transcribe-audio-to-text", "Transcribe") + ".",
            "Keep the original .amr file in case you need it later.",
        ],
        "faq": [
            ("What is an AMR file?", "AMR stands for Adaptive Multi-Rate, a codec made for compressing speech on mobile networks. It is common in older phone voice recorders and some call-recording apps."),
            ("Why can't I open my .amr file?", "Most desktop players and editors don't include an AMR decoder by default. MP3 opens almost everywhere."),
            ("Will the sound improve after converting?", "No. Conversion changes the format, not the recorded detail. Noise reduction and normalizing can make speech clearer."),
            ("What file size can I upload?", "Free accounts can upload up to 15MB per file; Pro allows up to 20MB. AMR files are tiny, so this is rarely a problem."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start."),
        ],
        "related_tools": ["convert-audio-format", "remove-background-noise", "normalize-audio-volume", "transcribe-audio-to-text"],
        "blog_keywords": ["amr", "convert", "voice recording", "mp3"],
    },
    "wma-to-mp3": {
        "widget": "convert",
        "usage_key": "convert",
        "default_format": "mp3",
        "title": "WMA to MP3 Converter Online Free | VoxCraft",
        "meta_description": "Convert WMA to MP3 online free. Make Windows Media Audio files play on phones, Macs and any editor. No install, no signup.",
        "eyebrow": "WMA → MP3",
        "h1": "WMA to MP3 converter online — free",
        "sub": "Convert a Windows Media Audio (.wma) file to MP3 so it plays on phones, Macs and editing apps.",
        "intro": [
            "Convert WMA to MP3 online for free with VoxCraft. Upload a .wma file, keep MP3 selected, and download a file that plays on phones, Macs, car stereos and every mainstream editor — no install required.",
            "WMA (Windows Media Audio) is Microsoft's audio format. It was common in old Windows Media Player libraries, ripped CDs and some dictation and voice-recorder devices. Outside the Windows world, support is limited — many phones and apps simply skip .wma files.",
            "WMA and MP3 are both lossy, so converting between them re-encodes the audio. Pick a bitrate at least as high as the original so you don't lose more than necessary; 192 kbps is a safe choice for music and 128 kbps for speech.",
            "If your goal is editing, you can also convert to WAV, which doesn't compress the audio again, then trim or clean it before exporting a final MP3.",
        ],
        "how_it_works": [
            "Upload your .wma file (15MB max, 20MB with Pro).",
            "Choose MP3 (or WAV if you plan to edit) and set the quality.",
            "Tap Convert and wait a few seconds.",
            "Download the converted file.",
        ],
        "use_cases": [
            ("Old music libraries", "Make ripped or downloaded .wma tracks playable on a phone."),
            ("Dictation and voice recorders", "Convert recorder files so they open in standard editors and transcription services."),
            ("Editing", "Convert to WAV or MP3 for video and audio editors that don't import .wma."),
        ],
        "tips": [
            "Don't choose a lower bitrate than the source unless you want a smaller file.",
            "Converting lossy to lossy can't restore quality; keep the original if it matters.",
            "Need to join several tracks afterwards? Use " + _a("merge-audio-files", "Merge") + ".",
            "Protected (DRM) WMA files can't be converted and will fail to load.",
        ],
        "faq": [
            ("What is WMA?", "Windows Media Audio is a compressed audio format developed by Microsoft."),
            ("Why won't WMA play on my phone?", "Many phones and apps don't support it. MP3 is supported nearly everywhere."),
            ("Will I lose quality?", "Converting between two lossy formats re-encodes the audio, so there is a small loss. A bitrate equal to or above the original keeps it minimal."),
            ("Can I convert DRM-protected WMA?", "No. Files protected by DRM can't be decoded by this tool."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start. Free uploads are limited to 15MB per file; Pro allows 20MB."),
        ],
        "related_tools": ["convert-audio-format", "compress-audio", "merge-audio-files", "trim-cut-audio"],
        "blog_keywords": ["wma", "convert", "mp3", "format"],
    },
    "m4a-to-wav": {
        "widget": "convert",
        "usage_key": "convert",
        "default_format": "wav",
        "title": "M4A to WAV Converter Online Free | VoxCraft",
        "meta_description": "Convert M4A to WAV online free. Turn iPhone Voice Memos and AAC audio into uncompressed WAV for editing. No install, no signup.",
        "eyebrow": "M4A → WAV",
        "h1": "M4A to WAV converter online — free",
        "sub": "Turn an .m4a file — such as an iPhone Voice Memo — into an uncompressed WAV for editing or software that doesn't accept M4A.",
        "intro": [
            "Convert M4A to WAV online for free with VoxCraft. Upload an .m4a file, keep WAV selected, and download an uncompressed file that works in editors, DAWs and tools that reject M4A — no install and no signup on the free tier.",
            "M4A is an audio file in the MP4 container, usually AAC-compressed. iPhone Voice Memos, iTunes/Apple Music downloads and many voice recorders produce it. It is great for storage, but some editing software, game engines and transcription or speech tools want plain WAV.",
            "WAV stores audio uncompressed, so the file will be several times larger than the M4A. That's expected. It doesn't bring back detail lost to AAC compression; what it does is stop further quality loss while you edit.",
            "A common workflow: convert to WAV, trim or clean the recording, then export a final MP3 or M4A at the end. See " + _a("trim-cut-audio", "trim") + " and " + _a("remove-background-noise", "noise reduction") + ".",
        ],
        "how_it_works": [
            "Upload your .m4a file (15MB max, 20MB with Pro).",
            "Leave the output format on WAV.",
            "Tap Convert and wait a moment.",
            "Download the WAV file.",
        ],
        "use_cases": [
            ("iPhone Voice Memos", "Get a WAV from a voice memo for an editor that doesn't take M4A."),
            ("Editing and mastering", "Work from an uncompressed file while you trim, clean and level audio."),
            ("Software compatibility", "Satisfy tools that only accept WAV input."),
        ],
        "tips": [
            "Expect a WAV to be many times the size of the original M4A.",
            "A 15MB upload limit applies to the M4A you upload, not to the WAV you receive.",
            "Keep the original M4A; the WAV can't recreate detail the AAC encode removed.",
            "Export to MP3 only once at the end to avoid stacking lossy re-encodes.",
        ],
        "faq": [
            ("What is an M4A file?", "An audio file stored in the MP4 container, usually compressed with AAC. Apple devices use it widely."),
            ("Why convert M4A to WAV?", "For editing software, DAWs and tools that need plain uncompressed audio."),
            ("Does WAV sound better than M4A?", "Not by itself. WAV avoids further compression, but it can't restore what the original M4A discarded."),
            ("Why is the WAV so large?", "WAV is uncompressed, so size grows with duration. That's normal."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start."),
        ],
        "related_tools": ["convert-audio-format", "decompress-audio", "trim-cut-audio", "remove-background-noise"],
        "blog_keywords": ["m4a", "wav", "convert", "voice memo"],
    },
    "ogg-to-wav": {
        "widget": "convert",
        "usage_key": "convert",
        "default_format": "wav",
        "title": "OGG to WAV Converter Online Free | VoxCraft",
        "meta_description": "Convert OGG to WAV online free. Turn Ogg Vorbis audio into uncompressed WAV for editors and software. No install, no signup.",
        "eyebrow": "OGG → WAV",
        "h1": "OGG to WAV converter online — free",
        "sub": "Convert an Ogg Vorbis (.ogg) file to uncompressed WAV for editing or for software that doesn't read OGG.",
        "intro": [
            "Convert OGG to WAV online for free with VoxCraft. Upload an .ogg file, keep WAV selected, and download an uncompressed file for editors, DAWs and apps that don't read OGG — no install and no account on the free tier.",
            "OGG usually holds audio compressed with the Vorbis codec. You see it in games, open-source tools, web audio and Audacity exports. Plenty of commercial editors, hardware samplers and some phones expect WAV or MP3 instead.",
            "As with any lossy-to-lossless conversion, the WAV can't recover detail the OGG discarded; it simply gives you a stable, uncompressed file to work from. If you only need broad compatibility rather than editing, " + _a("convert-audio-format", "convert to MP3") + " gives a much smaller file.",
        ],
        "how_it_works": [
            "Upload your .ogg file (15MB max, 20MB with Pro).",
            "Leave the output format on WAV.",
            "Tap Convert.",
            "Download the WAV file.",
        ],
        "use_cases": [
            ("Game and sample audio", "Convert OGG assets for editors or samplers that only read WAV."),
            ("Editing", "Start from an uncompressed file when trimming or processing."),
            ("Compatibility", "Open OGG audio in software that doesn't support Vorbis."),
        ],
        "tips": [
            "WAV files are large — expect a big jump in size.",
            "Use MP3 instead if you only need playback compatibility.",
            "Keep the original OGG; it's the smaller, equivalent-quality copy.",
            "If your file is an Opus-in-Ogg voice note, see " + _a("opus-to-mp3", "Opus to MP3") + ".",
        ],
        "faq": [
            ("What is an OGG file?", "A container most often holding Vorbis-compressed audio, an open alternative to MP3."),
            ("Does OGG to WAV improve quality?", "No. It changes the format, not the detail that was lost when the OGG was created."),
            ("Why is the WAV much larger?", "WAV is uncompressed."),
            ("What size can I upload?", "Free accounts can upload up to 15MB per file; Pro allows up to 20MB."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start."),
        ],
        "related_tools": ["convert-audio-format", "decompress-audio", "compress-audio", "trim-cut-audio"],
        "blog_keywords": ["ogg", "wav", "convert", "vorbis"],
    },

    # ------------------------------------------------------------------
    # Video -> audio extractors (videoxtract widget)
    # ------------------------------------------------------------------
    "mov-to-mp3": {
        "widget": "videoxtract",
        "usage_key": "videoxtract",
        "default_format": "mp3",
        "title": "MOV to MP3 Converter Online Free — iPhone Video to Audio | VoxCraft",
        "meta_description": "Convert MOV to MP3 online free. Extract audio from iPhone and QuickTime videos as MP3 or WAV. No install, no signup.",
        "eyebrow": "MOV → MP3",
        "h1": "MOV to MP3 converter online — free",
        "sub": "Extract the audio from an iPhone or QuickTime .mov video as an MP3 or WAV — up to 50MB.",
        "intro": [
            "Convert MOV to MP3 online for free with VoxCraft. Upload an iPhone or QuickTime .mov video, choose MP3 (or WAV), and download just the soundtrack — no install and no signup on the free tier.",
            "MOV is the container Apple devices use for video. A phone recording, a screen recording from a Mac or a clip exported from an editor often ends up as .mov. When all you need is what was said — an interview, a lecture, a voice-over — pulling the audio out is easier to share, edit and transcribe than the whole video.",
            "Video uploads are capped at 50MB here. Phone video gets large quickly, so for longer recordings trim the clip first (the Photos app can shorten a video before you upload it) or extract in parts. Once you have the audio, you can " + _a("remove-background-noise", "clean up noise") + " or " + _a("transcribe-audio-to-text", "transcribe it") + ".",
            "Only extract audio from videos you own or have the right to use.",
        ],
        "how_it_works": [
            "Upload your .mov video (up to 50MB).",
            "Choose MP3 for sharing or WAV for further editing, and set the quality.",
            "Optionally set a start and end time to extract only part of the video.",
            "Tap Extract audio and download the result.",
        ],
        "use_cases": [
            ("iPhone interviews", "Turn a recorded video interview into an audio file for a podcast or notes."),
            ("Lectures and meetings", "Pull the audio from a recorded session to listen back or transcribe."),
            ("Voice-overs", "Reuse the narration from a screen recording as a standalone track."),
        ],
        "tips": [
            "Use WAV if you plan to denoise or edit; MP3 is better for sharing.",
            "If your video is over 50MB, shorten it first or use the start/end time fields on shorter pieces.",
            "Level out quiet recordings with " + _a("normalize-audio-volume", "Normalize") + " after extracting.",
            "Extracting audio doesn't change your original video.",
        ],
        "faq": [
            ("Can I convert an iPhone video to MP3?", "Yes. iPhone videos are usually .mov; upload the file (up to 50MB) and choose MP3."),
            ("What's the file size limit?", "50MB for video files. Trim or shorten longer recordings first."),
            ("Does it keep the video quality?", "The output is audio only; your original video is untouched."),
            ("MP3 or WAV?", "MP3 for small, shareable files; WAV for editing."),
            ("Can I extract only part of the video?", "Yes — use the optional start and end time fields before extracting."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start."),
        ],
        "related_tools": ["extract-audio-from-video", "mkv-to-mp3", "remove-background-noise", "transcribe-audio-to-text"],
        "blog_keywords": ["mov", "extract audio", "iphone", "video to mp3"],
    },
    "mkv-to-mp3": {
        "widget": "videoxtract",
        "usage_key": "videoxtract",
        "default_format": "mp3",
        "title": "MKV to MP3 Converter Online Free — Extract Audio | VoxCraft",
        "meta_description": "Convert MKV to MP3 online free. Extract the audio track from Matroska videos and screen recordings as MP3 or WAV. No signup.",
        "eyebrow": "MKV → MP3",
        "h1": "MKV to MP3 converter online — free",
        "sub": "Extract the soundtrack from an .mkv (Matroska) video as MP3 or WAV — up to 50MB.",
        "intro": [
            "Convert MKV to MP3 online for free with VoxCraft. Upload an .mkv video (up to 50MB), pick MP3 or WAV, and download only the audio — no install and no signup on the free tier.",
            "MKV (Matroska) is a flexible video container used for screen recordings — OBS can record straight to it — as well as for videos you've downloaded or ripped from your own discs. Many audio tools and phones don't accept it, so extracting the audio is the practical way to reuse a voice-over, a talk or music you have the rights to.",
            "MKV files can hold several audio tracks; this tool extracts a single main audio track rather than all of them. A 50MB cap applies to uploads, so for long recordings cut the video into shorter parts first.",
            "Respect copyright: extract audio only from material you own or are licensed to use.",
        ],
        "how_it_works": [
            "Upload your .mkv file (up to 50MB).",
            "Pick MP3 for sharing or WAV for editing.",
            "Optionally set start and end times for just part of the file.",
            "Tap Extract audio and download.",
        ],
        "use_cases": [
            ("Screen recordings", "Pull the narration from an OBS recording into its own audio file."),
            ("Talks and tutorials", "Make an audio-only version of a long talk you can listen to."),
            ("Transcription prep", "Extract the audio, then run it through the transcribe tool."),
        ],
        "tips": [
            "Use WAV when you plan to clean noise or edit; MP3 for sharing.",
            "If the file is too large, split the video into shorter parts first.",
            "Normalize after extracting if the recording is too quiet.",
            "Only the main audio track is extracted.",
        ],
        "faq": [
            ("What is an MKV file?", "A Matroska video container that can hold video, multiple audio tracks and subtitles."),
            ("Which audio track is extracted?", "The main/default audio track."),
            ("What is the size limit?", "50MB per video."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start."),
            ("Is it OK to extract audio from any video?", "Only from videos you own or have permission to use."),
        ],
        "related_tools": ["extract-audio-from-video", "mov-to-mp3", "webm-to-mp3", "normalize-audio-volume"],
        "blog_keywords": ["mkv", "extract audio", "video to mp3"],
    },
    "webm-to-mp3": {
        "widget": "videoxtract",
        "usage_key": "videoxtract",
        "default_format": "mp3",
        "title": "WebM to MP3 Converter Online Free — Extract Audio | VoxCraft",
        "meta_description": "Convert WebM to MP3 online free. Extract audio from browser recordings and WebM videos as MP3 or WAV. No install, no signup.",
        "eyebrow": "WebM → MP3",
        "h1": "WebM to MP3 converter online — free",
        "sub": "Extract the audio from a .webm video or browser recording as MP3 or WAV — up to 50MB.",
        "intro": [
            "Convert WebM to MP3 online for free with VoxCraft. Upload a .webm file (up to 50MB), choose MP3 or WAV, and download the audio — no install and no signup on the free tier.",
            "WebM is a video format built for the web. Browser-based screen and meeting recorders, and many online tools, save recordings as .webm. The sound inside is typically Opus or Vorbis, which plenty of editors and phones can't open on its own.",
            "Extracting the audio gives you a normal MP3 or WAV you can edit, share or transcribe. Recordings made in a browser often have a little background noise — run the result through " + _a("remove-background-noise", "noise reduction") + " if needed.",
        ],
        "how_it_works": [
            "Upload your .webm file (up to 50MB).",
            "Choose MP3 or WAV and set the quality.",
            "Optionally set start and end times.",
            "Tap Extract audio and download.",
        ],
        "use_cases": [
            ("Browser recordings", "Turn a screen or meeting recording into an audio file."),
            ("Web video clips", "Extract the soundtrack from a WebM you created or own."),
            ("Podcast clips", "Get an MP3 from a recorded interview."),
        ],
        "tips": [
            "Choose WAV if you plan to denoise or edit.",
            "Large recordings: cut them into parts under 50MB.",
            "Add " + _a("normalize-audio-volume", "Normalize") + " if levels are uneven.",
            "Original WebM stays unchanged.",
        ],
        "faq": [
            ("What is WebM?", "An open video format designed for the web, typically holding VP8/VP9 video with Vorbis or Opus audio."),
            ("What is the size limit?", "50MB per video."),
            ("MP3 or WAV?", "MP3 for sharing; WAV for editing."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start."),
        ],
        "related_tools": ["extract-audio-from-video", "mkv-to-mp3", "remove-background-noise", "convert-audio-format"],
        "blog_keywords": ["webm", "extract audio", "video to mp3"],
    },

    # ------------------------------------------------------------------
    # Use-case pages on existing widgets
    # ------------------------------------------------------------------
    "whatsapp-voice-note-to-text": {
        "widget": "transcribe",
        "usage_key": "transcribe",
        "title": "WhatsApp Voice Note to Text — Urdu & Hindi, Free | VoxCraft",
        "meta_description": "Turn WhatsApp voice messages into text online free. Transcribe Urdu, Hindi or English voice notes (.opus). No install, no signup.",
        "eyebrow": "Voice note → Text",
        "h1": "WhatsApp voice note to text — Urdu, Hindi & English",
        "sub": "Upload a saved WhatsApp voice message and get a text transcript — Urdu and Hindi are first-choice languages.",
        "intro": [
            "Turn a WhatsApp voice note into text online for free with VoxCraft. Save the voice message from WhatsApp, upload it here, pick Urdu, Hindi or English, and get a transcript you can copy or download — no install and no account on the free tier.",
            "Voice notes are quick to record and tedious to listen back to, especially long ones. A transcript lets you skim, search and quote the message without replaying it. It also helps when you can't play audio — in a meeting, on a train, or when a message is in a language you read better than you hear.",
            "WhatsApp stores voice messages as Opus audio (usually .opus). VoxCraft reads them directly, so you don't need to convert first; if you'd like an MP3 copy as well, use " + _a("opus-to-mp3", "Opus to MP3") + ".",
            "Treat the result as a draft. Accuracy depends on how clearly the person speaks, background noise and accent, and Urdu/Hindi mixed with English words is harder than one language at a time. Check names and numbers against the audio.",
        ],
        "how_it_works": [
            "In WhatsApp, long-press the voice message and save or share it to your files (the exact menu depends on your phone).",
            "Upload the file here (15MB max, 20MB with Pro).",
            "Choose the spoken language — Urdu and Hindi are listed first.",
            "Tap Transcribe, then copy the text or download it as a .txt file.",
        ],
        "use_cases": [
            ("Long voice messages", "Read a two-minute voice note in seconds instead of replaying it."),
            ("Urdu and Hindi speakers", "Get Urdu or Hindi voice notes as text without typing them out."),
            ("Records and follow-up", "Keep a searchable written copy of an important instruction or order."),
        ],
        "tips": [
            "Choose the language that matches the speaker; it noticeably improves accuracy.",
            "If the recording is noisy, try " + _a("remove-background-noise", "noise reduction") + " first.",
            "Check names, numbers and addresses against the audio before relying on them.",
            "Very long notes can be cut into parts with the " + _a("trim-cut-audio", "trim tool") + ".",
        ],
        "faq": [
            ("Can I upload a WhatsApp voice message directly?", "Yes — save the voice message to your device and upload the file. WhatsApp voice notes are Opus audio, which VoxCraft can read."),
            ("Does it support Urdu and Hindi?", "Yes. Urdu and Hindi are first-choice languages, alongside English and others in the list."),
            ("How accurate is it?", "Good on clear, single-language speech; weaker with heavy noise, overlapping voices or a mix of languages. Always review the draft."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start."),
            ("What is the size limit?", "15MB per file on Free, 20MB with Pro."),
            ("Are my messages stored?", "See the <a href='/privacy' style='color:var(--brass-hi)'>privacy policy</a> for how uploads are handled."),
        ],
        "related_tools": ["transcribe-audio-to-text", "opus-to-mp3", "remove-background-noise", "trim-cut-audio"],
        "blog_keywords": ["transcri", "whatsapp", "voice message", "urdu"],
    },
    "ringtone-maker": {
        "widget": "cutter",
        "usage_key": "cutter",
        "title": "Ringtone Maker Online Free — Cut an MP3 into a Ringtone | VoxCraft",
        "meta_description": "Make a ringtone from an MP3 online free. Cut the exact part of a song or recording you want and download it as an MP3. No install.",
        "eyebrow": "Ringtone maker",
        "h1": "Ringtone maker online — cut an MP3 into a ringtone",
        "sub": "Pick the start and end of the part you want, trim it, and download a short MP3 you can use as a ringtone or alert tone.",
        "intro": [
            "Make a ringtone from an MP3 online for free with VoxCraft. Upload a song or recording, set the start and end of the part you want, and download a short MP3 — no install and no signup on the free tier.",
            "Ringtones work best short. A clip of roughly 20–30 seconds covers the hook without dragging, so choose the part or the line you recognise instantly rather than a whole verse. Start a fraction of a second before the sound begins so the ringtone doesn't feel clipped.",
            "This tool exports MP3, which Android phones accept as a ringtone. iPhone ringtones use the M4R format, which this page does not produce — you'd need an extra step to convert the MP3 on your side.",
            "Only make ringtones from music or recordings you own or have the right to use.",
        ],
        "how_it_works": [
            "Upload your MP3 (or WAV, M4A, OGG, FLAC) — 15MB max, 20MB with Pro. The duration appears automatically.",
            "Keep Trim selected and enter the start and end time in seconds.",
            "Tap Apply and preview the result.",
            "Download the MP3, then set it as a ringtone in your phone's sound settings.",
        ],
        "use_cases": [
            ("Song hook", "Cut the 20–30 seconds you recognise and use it as a ringtone."),
            ("Message and alert tones", "Make a short, clear alert sound from a recording."),
            ("Voice clip", "Turn a short spoken line into a custom tone."),
        ],
        "tips": [
            "Aim for 20–30 seconds; shorter is fine for alert tones.",
            "Start just before the first sound for a clean beginning.",
            "Add a gentle " + _a("fade-audio", "fade-out") + " so the end doesn't cut off abruptly.",
            "If it sounds too quiet, use " + _a("normalize-audio-volume", "Normalize") + " or " + _a("adjust-audio-volume", "adjust volume") + ".",
        ],
        "faq": [
            ("How long should a ringtone be?", "Around 20–30 seconds is a sensible target; check your phone's limit."),
            ("What format is the output?", "MP3."),
            ("Does this work for iPhone?", "iPhone ringtones use M4R. This tool outputs MP3, so it is best for Android or for trimming the clip before converting it yourself."),
            ("Is it free?", "Yes within free-tier limits, with no account required to start."),
            ("Can I use any song?", "Only music and recordings you own or are licensed to use."),
        ],
        "related_tools": ["trim-cut-audio", "fade-audio", "normalize-audio-volume", "convert-audio-format"],
        "blog_keywords": ["ringtone", "trim", "cut"],
    },
    "remove-hum-from-audio": {
        "widget": "denoise",
        "usage_key": "denoise",
        "title": "Remove Hum, Hiss & Fan Noise from Audio Online Free | VoxCraft",
        "meta_description": "Remove hum, hiss and fan noise from a recording online free. Steady background noise reduction for voice memos and podcasts.",
        "eyebrow": "Hum & hiss removal",
        "h1": "Remove hum, hiss and fan noise from audio — free",
        "sub": "Reduce steady background noise — AC hum, fan whirr, tape-style hiss — from a voice recording. Upload, set a strength, download.",
        "intro": [
            "Remove hum, hiss and fan noise from audio online for free with VoxCraft. Upload a recording, set the strength, and download a quieter version — no install and no signup on the free tier.",
            "These three problems have one thing in common: the noise is steady. A fan, an air-conditioner, a refrigerator, electrical hum or a cheap microphone's hiss all produce a constant sound under the voice. Spectral noise reduction is built for exactly that, because it can learn what the constant part sounds like and turn it down.",
            "It is much less effective on sudden sounds — a door slam, a cough, a passing motorbike — and on other people talking, because those aren't steady. For messy real-world speech, Pro adds an AI Studio mode. See the main " + _a("remove-background-noise", "background noise remover") + " for the full explanation.",
            "Start gently. Too much reduction makes voices thin or watery; a moderate setting that makes the hum sit well below the voice usually sounds best.",
        ],
        "how_it_works": [
            "Upload your recording (15MB max, 20MB with Pro).",
            "Choose Standard (free) and set the strength — start around the middle.",
            "Tap Remove noise and listen to the result.",
            "If the noise is still obvious, increase the strength a little; if the voice sounds thin, back off. Then download.",
        ],
        "use_cases": [
            ("Fan or AC in the room", "Quieten a constant whirr behind a voice memo or video voice-over."),
            ("Mic hiss", "Reduce the hiss from a budget microphone or a quiet recording boosted in volume."),
            ("Electrical hum", "Tone down mains hum picked up by a cable or a laptop."),
        ],
        "tips": [
            "It works best when there's a stretch of steady noise to learn from.",
            "Reduce noise before you boost volume; boosting first makes noise louder too.",
            "Record in a quieter spot or move away from the fan next time — prevention beats repair.",
            "Pair it with " + _a("normalize-audio-volume", "Normalize") + " afterwards to bring the level back up.",
        ],
        "faq": [
            ("Can it remove hum completely?", "It can reduce it a lot, but heavy settings affect the voice. Aim for much quieter, not silent."),
            ("Does it work on hiss?", "Yes. Constant hiss is one of the easiest things for spectral noise reduction to lower."),
            ("What about wind or sudden noises?", "Those aren't steady, so Standard mode handles them poorly."),
            ("Is it free?", "Standard mode is free within free-tier limits with no account required; Studio AI mode is Pro."),
            ("What formats work?", "Common formats such as MP3, WAV, M4A. Free uploads up to 15MB; Pro 20MB. Output is mono."),
        ],
        "related_tools": ["remove-background-noise", "normalize-audio-volume", "simple-audio-eq", "transcribe-audio-to-text"],
        "blog_keywords": ["noise", "hum", "hiss", "denoise"],
    },
}

# Display order for the "Convert by format" / use-case group on /tools.
FORMAT_PAGE_ORDER = [
    "opus-to-mp3", "amr-to-mp3", "wma-to-mp3", "m4a-to-wav", "ogg-to-wav",
    "mov-to-mp3", "mkv-to-mp3", "webm-to-mp3",
    "whatsapp-voice-note-to-text", "ringtone-maker", "remove-hum-from-audio",
]
