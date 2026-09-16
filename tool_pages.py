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
        "title": "Urdu & Hindi Speech to Text — Free Audio Transcription | VoxCraft",
        "meta_description": "Transcribe Urdu, Hindi, or English audio to text online, free. Turn WAV, MP3, M4A, OGG or FLAC recordings into text for voice memos, interviews, lectures and podcasts.",
        "eyebrow": "Audio → Text",
        "h1": "Transcribe Urdu, Hindi, or English audio to text — free",
        "sub": "Upload a recording and get a text transcript back, with Urdu and Hindi as first-choice languages. No install, no account required for free-tier use.",
        "intro": [
            "Transcribe Urdu, Hindi, or English audio to text online for free with VoxCraft. Upload a WAV, MP3, M4A, OGG or FLAC recording and get a readable transcript back — no install and no account required on the free tier.",
            "Urdu and Hindi sit at the top of the language list rather than buried in a long dropdown — most general-purpose transcription tools treat South Asian languages as an afterthought, but they're first-choice options here.",
            "VoxCraft's transcriber accepts WAV, MP3, M4A, OGG and FLAC files up to 10MB, and processes longer recordings in chunks so a 20-minute interview works the same way as a 30-second clip.",
        ],
        "how_it_works": [
            "Upload your audio file (WAV, MP3, M4A, OGG or FLAC, up to 10MB).",
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
            "Clear speech with minimal background noise transcribes far more accurately than noisy recordings — if your file is noisy, try the <a href=\"{denoise_url}\" style=\"color:var(--brass-hi)\">Denoise tool</a> first.",
            "For Urdu or Hindi audio, selecting the language explicitly (rather than auto-detect) usually gives more accurate results than letting the tool guess.",
            "Multiple overlapping speakers reduce accuracy — review the transcript rather than assuming perfect speaker separation.",
        ],
        "faq": [
            ("Is transcription free?", "Yes, within the free-tier daily limit shown above the tool. Pro removes the daily cap."),
            ("Does it support Urdu and Hindi speech to text?", "Yes — Urdu and Hindi are listed first in the language dropdown, ahead of other supported languages."),
            ("What other languages are supported?", "Check the language dropdown in the tool above for the current full list."),
            ("Are my files stored after transcribing?", "See our <a href=\"{privacy_url}\" style=\"color:var(--brass-hi)\">privacy policy</a> for exactly how long uploaded audio is retained."),
        ],
        "related_tools": ["remove-background-noise", "convert-audio-format", "extract-audio-from-video"],
        "blog_keywords": ["transcri", "speech to text", "subtitle"],
    },
    "convert-audio-format": {
        "widget": "convert",
        "usage_key": "convert",
        "title": "Convert Audio Format Online Free — MP3, WAV, OGG, M4A, FLAC | VoxCraft",
        "meta_description": "Convert audio format online free. Change between MP3, WAV, OGG, M4A and FLAC with adjustable bitrate. No install, no signup.",
        "eyebrow": "Format Conversion",
        "h1": "Convert audio format online — free",
        "sub": "Change format and bitrate in one step — useful when a platform, editor, or device only accepts a specific file type.",
        "intro": [
            "Convert audio format online for free with VoxCraft. Change between MP3, WAV, OGG, FLAC and other common formats in the browser — pick an output type and bitrate, then download. No install or signup required on the free tier. A video editor might want WAV, a podcast host might want MP3 at a specific bitrate, and an archival copy might call for lossless FLAC — this tool converts between the five most common formats in one step.",
            "You also control bitrate for lossy formats (64–320 kbps), so you can trade file size against audio quality depending on where the file is going.",
        ],
        "how_it_works": [
            "Upload your source file (WAV, MP3, OGG, M4A or FLAC, up to 10MB).",
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
            "Converting an already-compressed MP3 to another lossy format (or to FLAC) does not recover detail that compression already removed — start from the highest-quality source you have.",
            "Use WAV or FLAC when you plan to edit the file further; use MP3 for final, distribution-ready files where size matters.",
            "192 kbps MP3 is a reasonable default for spoken-word content; music generally benefits from 256–320 kbps.",
        ],
        "faq": [
            ("What's the max file size?", "10MB per file on the free tool. For larger files, try compressing first or splitting with the Cutter."),
            ("Does converting to a lossless format improve quality?", "No — converting a lossy file to FLAC or WAV keeps the same quality, it just changes the container/encoding."),
            ("Can I batch-convert multiple files?", "Not yet on this tool — each conversion is one file at a time."),
        ],
        "related_tools": ["trim-cut-audio", "extract-audio-from-video", "merge-audio-files"],
        "blog_keywords": ["format", "mp3", "convert", "bitrate"],
    },
    "merge-audio-files": {
        "widget": "merge",
        "usage_key": "merge",
        "title": "Merge Audio Files Online Free — Audio Joiner, Combine Clips | VoxCraft",
        "meta_description": "Free online audio joiner. Merge audio files and combine multiple MP3, WAV or OGG clips into one track with optional silence gap. No install, no signup.",
        "eyebrow": "Combine Clips",
        "h1": "Merge audio files online — free",
        "sub": "Stitch clips together in order, with a configurable gap between them — no editing software required.",
        "intro": [
            "Merging combines two or more separate audio files into a single continuous track, in the order you add them, with a configurable silence gap between each clip — the same job an \"audio joiner\" does on other sites. It's the fastest way to stitch together intro + main content + outro, or combine several voice memos into one file, without opening a full editor.",
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
            ("Is there a limit on how many files I can merge?", "No hard limit on count, but each individual file must be under 10MB."),
            ("Can I reorder files after adding them?", "Currently you remove and re-add in the order you want — files merge top to bottom as listed."),
            ("What output formats are available?", "MP3, WAV, or OGG."),
        ],
        "related_tools": ["trim-cut-audio", "convert-audio-format", "remove-background-noise"],
        "blog_keywords": ["merge", "combine", "stitch"],
    },
    "trim-cut-audio": {
        "widget": "cutter",
        "usage_key": "cutter",
        "title": "Trim & Cut Audio Online Free — MP3 Cutter, Ringtone Maker | VoxCraft",
        "meta_description": "Trim audio online free. Cut MP3 and WAV clips to exact start/end points, or split one file in two, in your browser — works as an MP3 cutter or ringtone maker. No install needed.",
        "eyebrow": "Trim / Split",
        "h1": "Trim and cut audio online — free",
        "sub": "Cut down to exactly the range you need, or split one file into two at a chosen point.",
        "intro": [
            "The Cutter does two related jobs: trimming a clip down to a specific start/end range, and splitting one file into two separate files at a chosen timestamp. Upload a file and the tool reads its duration automatically, so you can see exactly how much room you have to work with before setting your times.",
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
            ("What file size limit applies?", "10MB, same as the other short-audio tools."),
            ("Does trimming lose quality?", "For lossy formats there's a small re-encode; for WAV, trimming is lossless."),
        ],
        "related_tools": ["merge-audio-files", "convert-audio-format", "remove-background-noise"],
        "blog_keywords": ["trim", "cut", "split"],
    },
    "remove-background-noise": {
        "widget": "denoise",
        "usage_key": "denoise",
        "title": "Remove Background Noise from Audio Online — Free Noise Reducer | VoxCraft",
        "meta_description": "Remove background noise, hiss, hum, fan and static from audio online for free. Standard spectral denoise, or Studio AI speech enhancement (Pro) — the same class of model behind Adobe Podcast Enhance.",
        "eyebrow": "Noise Reduction",
        "h1": "Remove background noise from audio online — free",
        "sub": "Standard spectral noise reduction with a strength slider, or Studio AI speech enhancement (Pro) for a real model-based clean-up pass.",
        "intro": [
            "Remove background noise from audio online for free with VoxCraft. Upload a recording, choose Standard or Studio (AI) mode, and download a cleaner version in seconds — no account required. Standard mode uses spectral noise reduction to pull down steady background noise (fan hum, room tone, AC, light hiss) while keeping speech intact. It's built for consistent background noise, not sudden one-off sounds like a door slam or a dog bark, which spectral methods can't reliably distinguish from the wanted signal.",
            "Studio mode (Pro/Pro+) runs DeepFilterNet, a genuine deep-learning speech-enhancement model rather than a bigger noise filter — the same class of AI behind tools like Adobe Podcast Enhance. It doesn't just subtract a noise profile from the spectrum; it reconstructs what the speech should sound like, which handles roomy, low-quality, or non-stationary recordings that spectral gating alone can't clean up.",
        ],
        "how_it_works": [
            "Upload your recording (up to 10MB — output is mono).",
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
            "Start around 0.4–0.5 strength in Standard mode and increase only if noise is still noticeable — aggressive settings can make voices sound processed or unnatural.",
            "Standard mode won't remove sudden noises (claps, coughs, door slams) — only steady background sound. Studio mode handles a wider range of noise types since it's reconstructing speech, not filtering a spectrum.",
            "Studio mode is capped at 6-minute files since it's a genuine AI model pass, not a quick filter — for longer files, use Standard.",
            "Denoise before, not after, converting to a lossy format for best results.",
        ],
        "faq": [
            ("What's the difference between Standard and Studio mode?", "Standard is spectral noise reduction — fast and free, good for steady hum/hiss. Studio (Pro/Pro+) runs DeepFilterNet, a real AI speech-enhancement model that reconstructs speech rather than filtering a noise profile out of it — closer to what Adobe Podcast Enhance and similar tools do."),
            ("Will this fix a recording ruined by loud noise?", "Standard mode reduces steady background noise but can't reconstruct speech buried under very loud or non-steady noise. Studio mode handles a wider range, but extremely damaged audio still has limits."),
            ("Why is the output mono?", "Both engines currently output a single mixed-down channel."),
            ("Can I undo if it sounds worse?", "Keep your original file — reprocess from the untouched source with a lower strength setting, or try the other engine."),
        ],
        "related_tools": ["transcribe-audio-to-text", "voice-changer", "convert-audio-format"],
        "blog_keywords": ["noise", "denoise", "clean", "ai enhancement", "deepfilternet"],
    },
    "voice-changer": {
        "widget": "voicechange",
        "usage_key": "voicechange",
        "title": "Voice Changer & Pitch Changer Online Free — Robot, Echo | VoxCraft",
        "meta_description": "Free online voice changer and pitch changer. Apply pitch shift, robot, echo, chipmunk or deep voice effects to any audio clip. No install, no signup.",
        "eyebrow": "Voice Effects",
        "h1": "Voice changer online — free pitch & effects",
        "sub": "Pitch shift, robot, echo, chipmunk or deep voice — five effects with adjustable parameters.",
        "intro": [
            "The Voice Changer applies a deliberate effect to a voice recording rather than trying to make it sound more natural. Pitch Shift changes pitch while keeping speaking speed the same, which is different from Chipmunk and Deep Voice, which intentionally change both pitch and speed together for a more exaggerated character effect. Robot and Echo layer processing effects on top of the original voice.",
        ],
        "how_it_works": [
            "Upload a voice clip (WAV, MP3, OGG or M4A, up to 10MB).",
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
        "title": "Audio Extractor — Extract Audio from Video Online Free | VoxCraft",
        "meta_description": "Free online audio extractor. Convert MP4, MOV, MKV or WEBM to MP3 or WAV in your browser. No signup required.",
        "eyebrow": "Video → Audio",
        "h1": "Extract audio from video online — free",
        "sub": "Pull the soundtrack out of MP4, AVI, MOV, MKV or WEBM — up to 50MB, since video files run larger.",
        "intro": [
            "Extract audio from video online for free with VoxCraft. Upload an MP4, MOV, WebM or similar file and download the audio track as MP3 or WAV — no install, no account required on the free tier. Use it to pull narration out of a screen recording or get a podcast-ready audio file from a video interview. Because video files are naturally larger than audio-only files, this tool allows uploads up to 50MB, higher than VoxCraft's other short-audio tools.",
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
            "If your video is over 50MB, trimming it down first (in a video editor) or reducing its resolution/bitrate can bring it under the limit.",
            "Corrupted or incomplete video uploads fail with a clear error rather than hanging — re-export the video if this happens.",
            "WAV output preserves the most detail if you plan to edit the extracted audio further.",
        ],
        "faq": [
            ("Why is the video limit higher than the audio tools?", "Video files are inherently larger even for a short clip, so a lower limit would make the tool unusable for typical files."),
            ("Does this work on screen recordings?", "Yes, as long as the format is MP4, AVI, MOV, MKV or WEBM."),
            ("Can I extract just part of the audio?", "Extract the full track first, then use <a href=\"{cutter_url}\" style=\"color:var(--brass-hi)\">Cutter</a> to trim it down."),
        ],
        "related_tools": ["convert-audio-format", "trim-cut-audio", "transcribe-audio-to-text"],
        "blog_keywords": ["video", "extract", "screen recording"],
    },
    "ai-music-generator": {
        "widget": "music",
        "usage_key": None,
        "title": "AI Music & Song Generator Online Free — Text to Music | VoxCraft",
        "meta_description": "Generate original AI music from a text prompt — instrumental or with sung vocals from lyrics. Free online AI song generator powered by ACE-Step, for videos and podcasts.",
        "eyebrow": "AI Music",
        "h1": "AI music generator — text to music online",
        "sub": "Describe genre, mood and instruments; get a real instrumental or vocal track back in under a minute. Pro+ feature.",
        "intro": [
            "VoxCraft's music generator is powered by ACE-Step, an Apache 2.0-licensed model, which means tracks generated here are safe for commercial use — always double-check the current licensing details before publishing anything commercially. Describe the style you want as comma-separated tags (genre, mood, instruments, tempo), optionally add structured lyrics, and get back a track between 10 and 120 seconds.",
        ],
        "how_it_works": [
            "Describe your track using style tags — e.g. \"lofi, chill, piano, 90 bpm, warm.\"",
            "Choose instrumental, or uncheck it and add lyrics using [verse]/[chorus]/[bridge] structure.",
            "Set duration (10–120 seconds) and tap Generate track.",
            "Wait roughly 30–60 seconds, then preview and download.",
        ],
        "use_cases": [
            ("YouTube background music", "Generate a royalty-free-feeling music bed matched to a video's mood without licensing stock tracks."),
            ("Podcast intros/outros", "Create a short, distinctive musical sting for show branding."),
            ("Prototyping", "Quickly test what a genre/mood combination sounds like before committing to a direction."),
            ("Short-form content", "Generate quick instrumental beds for Reels/Shorts/TikTok-style content."),
        ],
        "tips": [
            "Specific tags produce more predictable results than vague ones — \"lofi, chill, piano, 90 bpm\" gives the model more to work with than just \"chill music.\"",
            "For vocal tracks, structure lyrics clearly with [verse]/[chorus]/[bridge] tags so the model understands song structure.",
            "Shorter durations (10–30s) generate faster and are often enough for intros, transitions, or short-form video.",
        ],
        "faq": [
            ("Is this available on the free tier?", "No — AI music generation is a Pro+ feature. See <a href=\"{upgrade_url}\" style=\"color:var(--brass-hi)\">Upgrade</a> for plans."),
            ("Can I use generated tracks commercially?", "ACE-Step is Apache 2.0 licensed, which is generally commercial-friendly — confirm current terms before relying on this for a commercial release."),
            ("How long does generation take?", "Roughly 30–60 seconds per track, depending on length and current load."),
        ],
        "related_tools": ["voice-changer", "merge-audio-files", "convert-audio-format"],
        "blog_keywords": ["music", "ace-step", "generate"],
    },

    "normalize-audio-volume": {
        "widget": "normalize",
        "usage_key": "normalize",
        "title": "Normalize Audio Volume Online Free — LUFS Loudness Normalizer | VoxCraft",
        "meta_description": "Normalize audio volume online free. True LUFS loudness normalization (EBU R128) with Spotify/YouTube, podcast and broadcast presets, plus simple peak normalize. Ideal before publishing or merging.",
        "eyebrow": "Normalize",
        "h1": "Normalize audio volume online — free",
        "sub": "Bring quiet clips up and tame loud peaks — quick peak normalize, or true LUFS loudness matching to a streaming, podcast or broadcast target.",
        "intro": [
            "Two ways to level out audio, in one tool. Peak normalize is the fast option: gain is set so the loudest sample reaches a target dBFS. LUFS mode measures true perceived loudness per ITU-R BS.1770 / EBU R128 — the same standard Spotify, YouTube and podcast platforms use to decide whether to turn your upload up or down — and matches it to a target so two files with different dynamics still sound equally loud.",
            "Unlike a simple volume slider, both modes analyze the file and calculate the right gain automatically rather than asking you to guess.",
        ],
        "how_it_works": [
            "Upload an audio file (up to 10MB).",
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
            "Use this when you already know you want “about +3 dB more” or “turn this bed down a bit.” For automatic leveling across files, prefer Normalize.",
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
        "title": "Audio Speed Changer Online Free — Speed Up or Slow Down | VoxCraft",
        "meta_description": "Speed up or slow down audio online free (0.5×–2×). Keep pitch or allow shift. Perfect for Shorts, voice memos and practice.",
        "eyebrow": "Speed",
        "h1": "Change audio speed online — free",
        "sub": "Make a clip faster or slower in your browser — 0.5× to 2×.",
        "intro": [
            "Speeding up shortens duration; slowing down stretches it. By default pitch is preserved (time-stretch), so speech still sounds like the same person — better for voiceovers and Shorts.",
        ],
        "how_it_works": [
            "Upload an audio file up to 10MB.",
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
            "Hard starts and stops are noticeable in videos and podcasts. A short fade-in and fade-out is one of the easiest polish steps before publish.",
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
        "title": "Split Audio by Silence Online Free — Auto Splitter | VoxCraft",
        "meta_description": "Split audio by silence online free. Auto-cut long recordings into separate clips at pauses. Ideal for interviews and multi-take voiceovers.",
        "eyebrow": "Split",
        "h1": "Split audio by silence online — free",
        "sub": "Cut a long file into separate parts wherever there's a pause.",
        "intro": [
            "When you've recorded several takes in one file, or an interview with natural gaps, splitting on silence saves manual scrubbing in a full editor.",
        ],
        "how_it_works": [
            "Upload a recording up to 10MB.",
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
        "title": "Audio Reverser Online Free — Reverse & Play Audio Backwards | VoxCraft",
        "meta_description": "Free online audio reverser. Play any MP3 or WAV backwards in your browser. Instant reverse for effects, transitions and hidden messages.",
        "eyebrow": "Reverse",
        "h1": "Reverse audio online — free",
        "sub": "Play a clip backwards in one click.",
        "intro": ["Useful for effects, transitions, or checking material in reverse. Simple and fast."],
        "how_it_works": ["Upload a file (up to 10MB).", "Tap Reverse.", "Download the result."],
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
        "intro": ["Mono is often better for voice-only uploads, phone playback, and smaller file sizes."],
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
        "intro": ["Handy when a short bed or stinger needs to cover a longer section without opening a full DAW."],
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
        "intro": ["A light two-band EQ for quick fixes — not a replacement for a full studio parametric EQ."],
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
        "title": "AI Dubbing & Video Redub Online Free — Translate & Re-voice | VoxCraft",
        "meta_description": "Redub video online. Translate and replace spoken audio in 40+ languages with neural AI voices. AI video dubbing for creators.",
        "eyebrow": "Video redub",
        "h1": "Video redub online — AI translate & re-voice",
        "sub": "Upload a video, pick a target language and voice, get a new dubbed track muxed back onto the original picture. Pro plan.",
        "intro": [
            "Audio-only redub keeps the original picture and replaces the spoken track. The pipeline extracts audio, transcribes speech, translates the script, re-voices it with a stock neural voice, then muxes the new audio onto the video — all without needing a cloned voice or GPU time.",
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
    "transcribe-audio-to-text", "convert-audio-format", "merge-audio-files", "trim-cut-audio",
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
