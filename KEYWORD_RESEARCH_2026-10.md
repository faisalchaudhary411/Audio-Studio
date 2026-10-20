# VoxCraft keyword plan — audio tools first (Oct 2026)

**Strategy:** head terms ("mp3 cutter", "audio trimmer", "mp4 to mp3") are owned by sites with
millions of monthly visits (e.g. mp3cut.net ≈ 6.3M, audiotrimmer.com ≈ 1.5M per Semrush public
data). Rank first on narrower, lower-competition queries the existing tools already satisfy, then
return to TTS once the domain has some authority.

> Search volumes/difficulty were **not** measured (no Semrush/Ahrefs access). Difficulty is a
> judgement from who currently ranks. Validate in Google Search Console + Keyword Planner.

## Existing tool pages — retargeted
| Page | Primary keyword targets |
|---|---|
| /tools/split-audio-by-silence | split audio by silence online, split mp3 at silence |
| /tools/loop-audio | loop audio online free, repeat mp3 X times |
| /tools/reverse-audio | reverse audio online, reverse voice recording |
| /tools/stereo-to-mono | stereo to mono converter online, convert mp3 to mono |
| /tools/normalize-audio-volume | normalize audio to -16 LUFS, lufs normalizer online |
| /tools/adjust-audio-volume | increase mp3 volume online, audio volume booster |
| /tools/change-audio-speed | speed up audio without changing pitch |
| /tools/fade-audio | fade in fade out audio online |
| /tools/remove-background-noise | remove background noise from audio online |

## New landing pages (format_pages.py — reuse existing widgets, no new backend)
| Page | Targets | Widget |
|---|---|---|
| /tools/opus-to-mp3 | opus to mp3, whatsapp voice note to mp3 | convert |
| /tools/amr-to-mp3 | amr to mp3 | convert |
| /tools/wma-to-mp3 | wma to mp3 | convert |
| /tools/m4a-to-wav | m4a to wav | convert (WAV preselected) |
| /tools/ogg-to-wav | ogg to wav | convert (WAV preselected) |
| /tools/mov-to-mp3 | mov to mp3, iphone video to mp3 | videoxtract |
| /tools/mkv-to-mp3 | mkv to mp3 | videoxtract |
| /tools/webm-to-mp3 | webm to mp3 | videoxtract |
| /tools/whatsapp-voice-note-to-text | whatsapp voice message to text urdu/hindi | transcribe |
| /tools/ringtone-maker | make ringtone from mp3 | cutter |
| /tools/remove-hum-from-audio | remove hum / hiss / fan noise from audio | denoise |

## New tool
- /tools/bpm-key-finder — BPM + musical key estimate (librosa; `POST /api/tools/bpm`).

## Not done (and why)
- **Mute video / remove audio from video** — competitive keyword and the output is a large video
  file that would have to travel as base64 JSON like the audio tools do; needs a download-token
  flow (like redub) first.
- **Vocal remover / karaoke maker** — needs a real separation model; a cheap phase trick sounds poor.
- **Loop for hours** — target-length looping is built but capped at 20 min (MP3) / 5 min (WAV) because results are built in RAM and returned base64 in the response.

## Added later
- Loop tool: "repeat until target length" mode (`target_sec` on `/api/tools/loop`).
- Trim/cutter: optional M4R output (`output_format=m4r` on `/api/tools/cutter/trim`) for iPhone ringtones.

## Also fixed
- Every tool page `<title>` was rendered as "… | VoxCraft — VoxCraft"; now brand appears once.
- `/tools` and tool pages now set their own `og:title` / `og:description` (were inheriting the site default).
- Hub copy no longer hard-codes "Eighteen tools"; new "Convert by format" group on /tools.
- Upload `accept` lists include .opus/.amr/.wma/.3gp so file pickers show these files.

## After deploy
1. Submit https://voxcraft.site/sitemap.xml in Search Console (new URLs are included automatically).
2. Request indexing for the top pages: opus-to-mp3, whatsapp-voice-note-to-text, remove-hum-from-audio, mov-to-mp3.
3. Check Performance → Queries after 3–4 weeks and double down on pages that get impressions.
4. Keep every new format page backed by real, specific copy — thin near-duplicates are what AdSense rejected before.
