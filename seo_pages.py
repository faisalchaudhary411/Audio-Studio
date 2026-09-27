"""Content for VoxCraft's dedicated SEO landing pages.

These pages are informational entry points only. They reuse existing public
routes and tools, so adding or editing a page here cannot change audio, TTS,
payments, accounts, or usage-limit behaviour.
"""

import json
import os

SEO_PAGES = {'urdu-text-to-speech': {'title': 'Urdu Text to Speech Free — AI Voice Online | VoxCraft',
                         'meta_description': 'Free Urdu text to speech online. Paste your script, '
                                             'pick an Urdu neural voice, and download narration '
                                             'for YouTube or courses — no signup to start.',
                         'eyebrow': 'Urdu TTS',
                         'h1': 'Urdu text to speech (free AI voice)',
                         'intro': ['Need an Urdu voiceover without booking a mic? Open Voice '
                                   'Studio, choose an Urdu voice, paste your text, and generate. '
                                   'The free tier works without an account — good for testing a '
                                   'channel idea or shipping a short video the same day.',
                                   'Where cheap global TTS often slips: city names, numbers, and '
                                   'those English words you drop into an Urdu line (brand names, '
                                   'app titles). We treat Urdu as a normal workflow, not an '
                                   'afterthought. Write a real opening paragraph, generate 20–40 '
                                   'seconds, and listen on your phone. If something sounds off, '
                                   'fix the spelling and run that bit again before you do the '
                                   'whole script.',
                                   'Script tip: Nastaliq (Arabic script) usually reads cleaner '
                                   'than pure Roman Urdu. Roman is fine for a quick test, but '
                                   'check hard words carefully. When the file is ready, you can <a '
                                   'href="/tools/trim-cut-audio">trim</a>, <a '
                                   'href="/tools/merge-audio-files">merge</a>, or <a '
                                   'href="/tools/normalize-audio-volume">normalize</a> it with the '
                                   'free tools, then drop it into CapCut or Premiere.',
                                   'Building for YouTube? See <a '
                                   'href="/text-to-speech-for-youtube">TTS for YouTube</a> and <a '
                                   'href="/how-to-create-youtube-voiceover">how to create a '
                                   'YouTube voiceover</a>. Hindi channel too? <a '
                                   'href="/hindi-text-to-speech">Hindi text to speech</a> is next '
                                   'door. Commercial use of audio you generate is allowed under '
                                   'the current Terms — check that page and live limits on <a '
                                   'href="/pricing">pricing</a> if you upload a lot.'],
                         'steps': ['Open Voice Studio and pick Urdu in the language list.',
                                   'Preview two or three voices on the same short line from your '
                                   'real script (include one name and one number).',
                                   'Generate only the opening paragraph first. Listen on phone '
                                   'speakers, not just laptop earbuds.',
                                   'Fix spellings or punctuation where it tripped, then generate '
                                   'the rest in sections.',
                                   'Download the file. Trim, merge, or convert if you need to — '
                                   'then place it on your timeline.'],
                         'use_cases': [('YouTube & Shorts',
                                        'Faceless explainers and recaps that need steady Urdu '
                                        'narration without recording every day.'),
                                       ('Courses & lessons',
                                        'Turn written Urdu notes into audio people can listen to '
                                        'on the commute.'),
                                       ('Script checks',
                                        'Hear the pacing before you hire talent or record '
                                        'yourself.'),
                                       ('Urdu versions of English drafts',
                                        'You already translated the outline — this is the voice '
                                        'track.')],
                         'faq': [('Is Urdu text to speech free on VoxCraft?',
                                  'Yes. You can try Urdu voices without creating an account, '
                                  'within the free limits shown in Studio and on the pricing '
                                  'page.'),
                                 ('Which Urdu voice should I use?',
                                  'Preview with a line from your niche — news tone vs story time '
                                  'sound different. Pick what fits the audience, not the prettiest '
                                  'demo line.'),
                                 ('Can I mix English words in Urdu text?',
                                  'Yes. Always test a sample that includes those English bits; '
                                  'rewrite if a brand name gets mangled.'),
                                 ('Nastaliq or Roman Urdu?',
                                  'Native script is usually more reliable. Roman works for short '
                                  'tests if you listen carefully.'),
                                 ('Can I use this on monetized YouTube?',
                                  'Audio you generate is usable commercially under current Terms. '
                                  'Read the live Terms page for the full wording.'),
                                 ('Why does it sound flat sometimes?',
                                  'Long walls of text without punctuation don’t help. Shorter '
                                  'sentences and section-by-section generation sound more '
                                  'natural.'),
                                 ('What after I download the audio?',
                                  'Trim silence, merge intro/outro, denoise if needed, then edit '
                                  'video. The free toolset covers the common jobs.'),
                                 ('How is this different from random online TTS sites?',
                                  'Urdu isn’t buried at the bottom of a language list here. Studio '
                                  'plus the audio tools are meant for people who actually '
                                  'publish.')],
                         'cta_label': 'Try Urdu voices in Studio',
                         'related_links': [('Open Voice Studio', '/studio'),
                                           ('Hindi text to speech', '/hindi-text-to-speech'),
                                           ('Free text to speech', '/free-text-to-speech'),
                                           ('Text to speech for YouTube',
                                            '/text-to-speech-for-youtube'),
                                           ('Trim or cut audio', '/tools/trim-cut-audio'),
                                           ('Normalize volume', '/tools/normalize-audio-volume')]},
 'hindi-text-to-speech': {'title': 'Hindi Text to Speech Free — AI Voice Online | VoxCraft',
                          'meta_description': 'Free Hindi text to speech online. Paste Devanagari '
                                              '(or carefully tested Roman), pick a Hindi neural '
                                              'voice, and download narration — no signup to start.',
                          'eyebrow': 'Hindi TTS',
                          'h1': 'Hindi text to speech (free AI voice)',
                          'intro': ['Hindi voiceover without a recording booth: open Studio, '
                                    'select Hindi, paste your script, generate, download. Free '
                                    'tier doesn’t force a signup, so you can test a video idea the '
                                    'same afternoon.',
                                    'Quality shows up on names, prices, and English words sitting '
                                    'inside Hindi sentences. Don’t trust a single marketing demo '
                                    'line. Use 20–40 seconds of your real opening, listen on a '
                                    'phone, then decide if the voice fits.',
                                    'Type in Devanagari when you can — it usually beats pure Roman '
                                    'Hindi for pronunciation. After export, <a '
                                    'href="/tools/trim-cut-audio">trim</a>, <a '
                                    'href="/tools/merge-audio-files">merge</a>, or <a '
                                    'href="/tools/normalize-audio-volume">normalize</a> if the '
                                    'file needs a quick clean-up before the edit.',
                                    'Running Urdu and Hindi on the same channel? Test them '
                                    'separately; one setting rarely fits both. Related pages: <a '
                                    'href="/urdu-text-to-speech">Urdu text to speech</a>, <a '
                                    'href="/text-to-speech-for-youtube">TTS for YouTube</a>. '
                                    'Limits and commercial rules live on <a '
                                    'href="/pricing">pricing</a> and Terms.'],
                          'steps': ['Open Voice Studio and choose Hindi.',
                                    'Preview voices on a line that has a name and a number from '
                                    'your actual script.',
                                    'Generate a short opening first. Listen on phone speakers.',
                                    'Tweak rate or pitch if you need to, fix problem words, then '
                                    'generate the rest in sections.',
                                    'Export and drop the file into your editor.'],
                          'use_cases': [('YouTube explainers',
                                         'Educational and product videos that need clear Hindi '
                                         'narration.'),
                                        ('Online courses',
                                         'Lesson scripts turned into listen-along audio.'),
                                        ('Draft before you record',
                                         'Check pacing and awkward lines before a live session.'),
                                        ('Hindi track of an English outline',
                                         'Same structure, second language, faster ship.')],
                          'faq': [('Is Hindi text to speech free?',
                                   'Yes within free-tier limits. No account required to start.'),
                                  ('Should I use Devanagari?',
                                   'When you can, yes. Native script usually sounds clearer than '
                                   'pure Roman.'),
                                  ('Can I use the audio commercially?',
                                   'Yes under current Terms for audio you generate — read the live '
                                   'Terms page.'),
                                  ('What about voice cloning?',
                                   'Cloning is a separate Pro+ flow. Stock Hindi neural voices are '
                                   'in Studio on free/Pro as published.'),
                                  ('How long should a test sample be?',
                                   'About 20–40 seconds of real script beats one polished demo '
                                   'sentence.'),
                                  ('Numbers sound wrong — what now?',
                                   'Write them as words for critical lines, or split the sentence '
                                   'and regenerate only that part.'),
                                  ('Where is the full Hindi voice list?',
                                   'Inside Studio’s language and voice pickers. The live list is '
                                   'the source of truth.')],
                          'cta_label': 'Try Hindi voices in Studio',
                          'related_links': [('Open Voice Studio', '/studio'),
                                            ('Urdu text to speech', '/urdu-text-to-speech'),
                                            ('Free text to speech', '/free-text-to-speech'),
                                            ('How to create a YouTube voiceover',
                                             '/how-to-create-youtube-voiceover'),
                                            ('Normalize volume', '/tools/normalize-audio-volume'),
                                            ('Merge audio files', '/tools/merge-audio-files')]},
 'punjabi-text-to-speech': {'title': 'Punjabi Text to Speech Free — AI Voice Online | VoxCraft',
                            'meta_description': 'Free Punjabi text to speech online. Paste '
                                                'Gurmukhi, pick a neural voice, download narration '
                                                'for YouTube or courses — no signup to start.',
                            'eyebrow': 'Punjabi TTS',
                            'h1': 'Punjabi text to speech (free AI voice)',
                            'intro': ['Want a Punjabi voiceover without recording? Open Studio, '
                                      'choose Punjabi, paste your text, generate, download. Free '
                                      'tier works without an account — useful for Shorts, '
                                      'explainers, or a first test for a diaspora channel.',
                                      'What usually trips TTS: village and family names, English '
                                      'product words, and numbers written only as digits. Generate '
                                      '20–40 seconds of real script (not a demo line), listen on '
                                      'your phone, then fix what sounds wrong.',
                                      'Gurmukhi usually reads better than pure Roman Punjabi. '
                                      'After export, <a href="/tools/trim-cut-audio">trim</a>, <a '
                                      'href="/tools/merge-audio-files">merge</a>, or <a '
                                      'href="/tools/normalize-audio-volume">normalize</a> if you '
                                      'need a quick clean-up. Also see <a '
                                      'href="/hindi-text-to-speech">Hindi</a> and <a '
                                      'href="/urdu-text-to-speech">Urdu</a> if you publish more '
                                      'than one language.'],
                            'steps': ['Open Voice Studio and select Punjabi.',
                                      'Preview two voices on the same short line from your real '
                                      'script (one name, one number).',
                                      'Generate only the opening; listen on phone speakers.',
                                      'Fix spellings or rewrite awkward English loanwords, then '
                                      'generate the rest in sections.',
                                      'Download and trim/merge before the video edit.'],
                            'use_cases': [('Punjabi YouTube & Shorts',
                                           'Explainers and recaps aimed at Punjabi viewers in '
                                           'India, Pakistan, and the diaspora.'),
                                          ('Community updates',
                                           'Local and overseas community videos without booking a '
                                           'studio every week.'),
                                          ('Learning drafts',
                                           'Hear written Punjabi lessons before a human record.'),
                                          ('Bilingual channels',
                                           'A Punjabi track next to Hindi or English versions of '
                                           'the same outline.')],
                            'faq': [('Is Punjabi text to speech free?',
                                     'Yes within free limits. No account required to start. See '
                                     'pricing for Pro quotas.'),
                                    ('Gurmukhi or Roman?',
                                     'Gurmukhi is usually clearer. Roman is fine for a quick test '
                                     'if you listen carefully.'),
                                    ('Can I mix English words?',
                                     'Yes — test brand names and tech terms in a short sample.'),
                                    ('Commercial use on YouTube?',
                                     'Generated audio is usable under current Terms. Check the '
                                     'live Terms page.'),
                                    ('Why does it sound flat?',
                                     'Shorter sentences and section-by-section generation help '
                                     'more than one long block.'),
                                    ('Where is the voice list?',
                                     'Inside Studio’s language and voice pickers.')],
                            'cta_label': 'Try Punjabi voices in Studio',
                            'related_links': [('Open Voice Studio', '/studio'),
                                              ('Hindi text to speech', '/hindi-text-to-speech'),
                                              ('Urdu text to speech', '/urdu-text-to-speech'),
                                              ('Free text to speech', '/free-text-to-speech'),
                                              ('Normalize volume',
                                               '/tools/normalize-audio-volume')]},
 'bengali-text-to-speech': {'title': 'Bengali Text to Speech Free — AI Voice Online | VoxCraft',
                            'meta_description': 'Free Bengali (Bangla) text to speech online. '
                                                'Native script, neural voices, download for '
                                                'YouTube or courses — no signup to start.',
                            'eyebrow': 'Bengali TTS',
                            'h1': 'Bengali text to speech (free AI voice)',
                            'intro': ['Bangla voiceover in the browser: pick Bengali in Studio, '
                                      'paste script, generate, download. Free tier doesn’t force '
                                      'signup — good for testing a channel idea the same day.',
                                      'Quality shows up on conjunct characters, place names, and '
                                      'English words inside Bengali sentences. A 20–40 second '
                                      'sample with those cases saves more time than regenerating a '
                                      'full episode later.',
                                      'After generation, creators often <a '
                                      'href="/tools/trim-cut-audio">trim</a> intros, <a '
                                      'href="/tools/merge-audio-files">merge</a> scenes, or <a '
                                      'href="/tools/normalize-audio-volume">normalize</a> for '
                                      'YouTube. Related: <a href="/hindi-text-to-speech">Hindi '
                                      'TTS</a>, <a href="/text-to-speech-for-youtube">TTS for '
                                      'YouTube</a>.'],
                            'steps': ['Open Voice Studio and choose Bengali.',
                                      'Preview voices on a line that includes a name and a number.',
                                      'Generate a short opening; listen on phone speakers.',
                                      'Fix spellings or punctuation, then produce the remaining '
                                      'sections.',
                                      'Export and assemble in your editor.'],
                            'use_cases': [('Bangla YouTube',
                                           'Educational explainers, tech reviews, faceless '
                                           'channels.'),
                                          ('Online courses',
                                           'Written lessons turned into listen-along audio.'),
                                          ('News-style recaps',
                                           'Steady narration for weekly summary videos.'),
                                          ('Localization',
                                           'Bengali versions of an English or Hindi outline.')],
                            'faq': [('Is Bengali TTS free?',
                                     'Yes within free-tier limits; no account required to start.'),
                                    ('Should I type in Bengali script?',
                                     'Yes when you can — native script usually beats pure Roman '
                                     'Bangla.'),
                                    ('English words inside Bengali?',
                                     'Common. Always test brand names in a short sample.'),
                                    ('Commercial use?',
                                     'Allowed for audio you generate under current Terms.'),
                                    ('How long should tests be?',
                                     '20–40 seconds of real script is enough to judge a voice.'),
                                    ('Next tools after TTS?',
                                     'Trim, merge, denoise, or convert — then edit video.')],
                            'cta_label': 'Try Bengali voices in Studio',
                            'related_links': [('Open Voice Studio', '/studio'),
                                              ('Hindi text to speech', '/hindi-text-to-speech'),
                                              ('Free text to speech', '/free-text-to-speech'),
                                              ('Text to speech for YouTube',
                                               '/text-to-speech-for-youtube'),
                                              ('Merge audio files', '/tools/merge-audio-files')]},
 'tamil-text-to-speech': {'title': 'Tamil Text to Speech Free — AI Voice Online | VoxCraft',
                          'meta_description': 'Free Tamil text to speech online. Paste Tamil '
                                              'script, pick a neural voice, download narration — '
                                              'no signup to start.',
                          'eyebrow': 'Tamil TTS',
                          'h1': 'Tamil text to speech (free AI voice)',
                          'intro': ['Tamil narration without a desktop app: open Studio, select '
                                    'Tamil, paste text, generate, download. Free tier is enough to '
                                    'test a video idea before you commit a full series.',
                                    'Formal vocabulary, English tech terms, and long compound '
                                    'words are where weaker engines slip. Keep spoken sentences '
                                    'shorter than written essays, and test proper nouns early.',
                                    'Practical path: draft → short sample → fix → full generate → '
                                    '<a href="/tools/trim-cut-audio">trim</a> / <a '
                                    'href="/tools/normalize-audio-volume">normalize</a>. Running a '
                                    'multi-language South India channel? See <a '
                                    'href="/telugu-text-to-speech">Telugu TTS</a> too.'],
                          'steps': ['Open Voice Studio and select Tamil.',
                                    'Preview two voices on a line from your actual niche.',
                                    'Generate 20–40 seconds; check names, places, and English '
                                    'product words.',
                                    'Adjust the script, then generate remaining sections by scene.',
                                    'Download and place on your timeline.'],
                          'use_cases': [('Tamil YouTube explainers',
                                         'Tech, finance, and education channels.'),
                                        ('Course audio', 'Lesson scripts for commute listening.'),
                                        ('Product demos',
                                         'Consistent product voice without daily studio time.'),
                                        ('Multilingual South India',
                                         'Tamil track alongside Telugu or English.')],
                          'faq': [('Is Tamil text to speech free?',
                                   'Yes within free-tier limits, no account required to start.'),
                                  ('Tamil script or Roman?',
                                   'Native Tamil script is strongly preferred.'),
                                  ('Monetized YouTube?',
                                   'Generated audio is commercially usable under current Terms — '
                                   'verify the Terms page.'),
                                  ('One word sounds wrong?',
                                   'Rewrite it, add punctuation, or split a long sentence, then '
                                   'regenerate that section.'),
                                  ('Voice cloning for Tamil?',
                                   'Stock Tamil voices are in Studio; cloning is a separate Pro+ '
                                   'flow when your plan allows.'),
                                  ('Where are all Tamil voices?',
                                   'Studio language selector — live list is authoritative.')],
                          'cta_label': 'Try Tamil voices in Studio',
                          'related_links': [('Open Voice Studio', '/studio'),
                                            ('Telugu text to speech', '/telugu-text-to-speech'),
                                            ('Free text to speech', '/free-text-to-speech'),
                                            ('How to create a YouTube voiceover',
                                             '/how-to-create-youtube-voiceover'),
                                            ('Normalize volume', '/tools/normalize-audio-volume')]},
 'telugu-text-to-speech': {'title': 'Telugu Text to Speech Free — AI Voice Online | VoxCraft',
                           'meta_description': 'Free Telugu text to speech online. Neural voices '
                                               'for YouTube and courses — download MP3, no signup '
                                               'to start.',
                           'eyebrow': 'Telugu TTS',
                           'h1': 'Telugu text to speech (free AI voice)',
                           'intro': ['Telugu voiceover from written text: Studio → Telugu → paste '
                                     '→ generate → download. No desktop install. Free tier works '
                                     'without signup.',
                                     'Watch English brand names, numeric prices, and formal vs '
                                     'casual tone. A sample that includes a price line and a '
                                     'product name tells you more than a poetic demo sentence.',
                                     'After TTS: <a href="/tools/trim-cut-audio">trim</a>, <a '
                                     'href="/tools/merge-audio-files">merge</a>, or <a '
                                     'href="/tools/remove-background-noise">denoise</a> if you '
                                     'mixed in a live recording. Also <a '
                                     'href="/tamil-text-to-speech">Tamil</a> and <a '
                                     'href="/kannada-text-to-speech">Kannada</a> if you publish '
                                     'across South India.'],
                           'steps': ['Open Voice Studio and choose Telugu.',
                                     'Preview voices on a real script line with a name and a '
                                     'number.',
                                     'Generate a short section first; listen on phone speakers.',
                                     'Fix problem words, then generate the rest by section.',
                                     'Export and align to your video timeline.'],
                           'use_cases': [('Telugu YouTube',
                                          'Explainers, reviews, faceless educational channels.'),
                                         ('EdTech', 'Course modules and revision audio.'),
                                         ('Regional marketing',
                                          'Product explainers for Telugu-speaking customers.'),
                                         ('Multi-language publish',
                                          'Same outline in Telugu, Tamil, and English.')],
                           'faq': [('Is Telugu TTS free?',
                                    'Yes within free-tier limits; no signup required to start.'),
                                   ('Native Telugu script?', 'Yes — prefer it over pure Roman.'),
                                   ('Commercial rights?',
                                    'Audio you generate is usable under current Terms.'),
                                   ('Numbers sound wrong?',
                                    'Write numbers as words for critical lines, or split the '
                                    'sentence and regenerate that clause.'),
                                   ('Need higher volume?',
                                    'Upgrade when free caps block your schedule — see pricing.'),
                                   ('Where is the voice list?', 'Inside Studio.')],
                           'cta_label': 'Try Telugu voices in Studio',
                           'related_links': [('Open Voice Studio', '/studio'),
                                             ('Tamil text to speech', '/tamil-text-to-speech'),
                                             ('Kannada text to speech', '/kannada-text-to-speech'),
                                             ('Free text to speech', '/free-text-to-speech'),
                                             ('Text to speech for YouTube',
                                              '/text-to-speech-for-youtube')]},
 'text-to-speech-for-youtube': {'title': 'Text to Speech for YouTube — Free AI Voiceover | '
                                         'VoxCraft',
                                'meta_description': 'Practical text to speech workflow for '
                                                    'YouTube: test a short opening, fix names and '
                                                    'numbers, generate in sections, then edit. '
                                                    'Urdu and Hindi supported.',
                                'eyebrow': 'YouTube Voiceover',
                                'h1': 'Text to speech for YouTube narration',
                                'intro': ['YouTube narration doesn’t need a full recording booth '
                                          'every time. Write for the ear, test the first 20–40 '
                                          'seconds, fix what sounds odd, then generate the rest in '
                                          'sections. Studio supports languages like Urdu and Hindi '
                                          'on a free tier with no forced signup.',
                                          'Where people go wrong: one giant 10-minute generate, '
                                          'zero listening, upload straight to the timeline. Treat '
                                          'AI voice like a voice-actor take — short tests first.',
                                          'When the file is ready, <a '
                                          'href="/tools/normalize-audio-volume">normalize '
                                          'loudness</a>, <a href="/tools/trim-cut-audio">trim</a>, '
                                          'or <a href="/tools/merge-audio-files">merge</a> intro '
                                          'and outro. Language pages: <a '
                                          'href="/urdu-text-to-speech">Urdu</a>, <a '
                                          'href="/hindi-text-to-speech">Hindi</a>.',
                                          'Faceless channels, explainers, and product reviews fit '
                                          'well. Heavy emotional documentary work may still need a '
                                          'human VO — TTS is a production tool, not a guarantee of '
                                          'cinematic acting.'],
                                'steps': ['Finish the script for spoken delivery (short sentences '
                                          'help).',
                                          'Generate only the first 20–40 seconds and listen on '
                                          'phone speakers.',
                                          'Fix names, numbers, and awkward phrases.',
                                          'Generate remaining sections; keep files labeled by '
                                          'scene.',
                                          'Trim/merge/normalize, then align to the timeline.'],
                                'use_cases': [('Faceless YouTube',
                                               'Consistent narration without daily recording.'),
                                              ('Explainers', 'Steady educational delivery.'),
                                              ('Multilingual channels',
                                               'Urdu, Hindi, or English variants of the same '
                                               'outline.')],
                                'faq': [('Is TTS allowed on monetized YouTube?',
                                         'YouTube allows AI-assisted content under its rules when '
                                         'you follow their policies; also follow VoxCraft Terms. '
                                         'Check YouTube Help for the latest.'),
                                        ('Generate the whole video at once?',
                                         'Section-by-section is safer and easier to retake.'),
                                        ('What loudness should I aim for?',
                                         'Normalize, then check on phone and laptop. Use the <a '
                                         'href="/tools/normalize-audio-volume">normalize '
                                         'tool</a>.'),
                                        ('Urdu or Hindi for my audience?',
                                         'Match the audience. Test both if the channel is '
                                         'bilingual.'),
                                        ('Is free tier enough for weekly uploads?',
                                         'Depends on length and how often you post. Watch '
                                         'in-product limits.'),
                                        ('How do I make TTS less obvious?',
                                         'Natural punctuation, moderate speed, and a human-edited '
                                         'script matter more than any single toggle.'),
                                        ('Can I mix TTS with my real voice?',
                                         'Yes — AI for drafts or secondary languages, human for '
                                         'flagship episodes is common.')],
                                'cta_label': 'Create a YouTube voiceover',
                                'related_links': [('Open Voice Studio', '/studio'),
                                                  ('How to create a YouTube voiceover',
                                                   '/how-to-create-youtube-voiceover'),
                                                  ('Audio tools for YouTubers',
                                                   '/audio-tools-for-youtubers'),
                                                  ('Normalize volume',
                                                   '/tools/normalize-audio-volume'),
                                                  ('Merge audio', '/tools/merge-audio-files')]},
 'free-text-to-speech': {'title': 'Free Text to Speech Online — No Signup | VoxCraft',
                         'meta_description': 'Free text to speech online with neural voices. Urdu, '
                                             'Hindi, English and more. Download narration — no '
                                             'account required to start.',
                         'eyebrow': 'Free TTS',
                         'h1': 'Free text to speech online',
                         'intro': ['Open Studio, pick a language and voice, paste text, generate, '
                                   'download. Free tier doesn’t need a card or an account to start '
                                   '— limits are shown in the product and on pricing.',
                                   '“Free TTS” tools vary on three things that matter: how natural '
                                   'the voice is, which languages are actually usable, and whether '
                                   'you can use the file commercially. VoxCraft is aimed at '
                                   'creators who need downloadable narration (including Urdu and '
                                   'Hindi) plus small audio tools around the file.',
                                   'Use free generation to test scripts and ship small projects. '
                                   'Move to Pro when daily limits block your schedule. See <a '
                                   'href="/pricing">pricing</a> for live numbers.',
                                   'Next: <a href="/urdu-text-to-speech">Urdu TTS</a>, <a '
                                   'href="/hindi-text-to-speech">Hindi TTS</a>, <a '
                                   'href="/text-to-speech-for-youtube">TTS for YouTube</a>, <a '
                                   'href="/tools">audio tools</a>.'],
                         'steps': ['Open Voice Studio (no account required on free).',
                                   'Pick language and voice; preview a sample.',
                                   'Paste a short test script and generate.',
                                   'Download and review on phone speakers.',
                                   'Check pricing if you need higher limits or cloning.'],
                         'use_cases': [('Quick tests', 'Compare voices on the same paragraph.'),
                                       ('Small projects', 'Short videos within free limits.'),
                                       ('Education',
                                        'Teachers and students trying narration ideas.')],
                         'faq': [('Do I need a credit card?',
                                  'No. Free tier doesn’t require signup or a card to start.'),
                                 ('Can I use free audio commercially?',
                                  'Generated audio is usable under current Terms — read the live '
                                  'Terms page.'),
                                 ('What are the free limits?',
                                  'They can change. Studio UI and pricing show current '
                                  'allowances.'),
                                 ('When should I upgrade?',
                                  'When you hit caps, need batch volume, or want Pro+ features '
                                  'like cloning.'),
                                 ('Which languages are free?',
                                  'Studio voice library under usage caps; Urdu and Hindi are '
                                  'first-class.'),
                                 ('Are downloads watermarked?',
                                  'You get the generated audio file under plan rules — not a promo '
                                  'watermark track.'),
                                 ('Vs browser read-aloud?',
                                  'Read-aloud is for listening. This is built for export and light '
                                  'editing.')],
                         'cta_label': 'Try free text to speech',
                         'related_links': [('Open Voice Studio', '/studio'),
                                           ('Urdu TTS', '/urdu-text-to-speech'),
                                           ('Hindi TTS', '/hindi-text-to-speech'),
                                           ('YouTube TTS workflow', '/text-to-speech-for-youtube'),
                                           ('All tools', '/tools')]},
 'how-to-create-youtube-voiceover': {'title': 'How to Create a YouTube Voiceover (Simple Workflow) '
                                              '| VoxCraft',
                                     'meta_description': 'A simple YouTube voiceover workflow: '
                                                         'write for the ear, test the opening, fix '
                                                         'hard words, generate or record in '
                                                         'sections, then match audio to video.',
                                     'eyebrow': 'Creator Guide',
                                     'h1': 'How to create a YouTube voiceover',
                                     'intro': ['A reliable voiceover starts before any tool. Clean '
                                               'script, short test, listen, then finish. That '
                                               'order saves more time than regenerating a whole '
                                               'episode later.',
                                               'The same steps work whether you use AI voice in '
                                               'Studio or record yourself: prepare → test → review '
                                               '→ edit → match the final audio to the picture.'],
                                     'steps': ['Write for the ear — short, natural sentences.',
                                               'Test the first 20–40 seconds before producing the '
                                               'full narration.',
                                               'Fix names, numbers, pacing, and difficult phrases.',
                                               'Generate or record the remaining sections; trim '
                                               'and merge as needed.',
                                               'Listen once with the finished video before you '
                                               'export.'],
                                     'use_cases': [('New creators',
                                                    'A repeatable process instead of improvising '
                                                    'every upload.'),
                                                   ('Faceless videos',
                                                    'Narration separate from the visual edit.'),
                                                   ('Team workflows',
                                                    'Script as the source of truth for '
                                                    'revisions.')],
                                     'faq': [('What should I test first?',
                                              'The opening, plus any line with names, dates, '
                                              'numbers, or unusual words.'),
                                             ('Why split into sections?',
                                              'Smaller pieces are easier to replace without '
                                              'redoing the whole project.'),
                                             ('What comes after narration?',
                                              'Check timing against the video, then small edits '
                                              'before export.')],
                                     'cta_label': 'Open Voice Studio',
                                     'related_links': [('Open Voice Studio', '/studio'),
                                                       ('Text to speech for YouTube',
                                                        '/text-to-speech-for-youtube'),
                                                       ('Audio tools for YouTubers',
                                                        '/audio-tools-for-youtubers'),
                                                       ('Urdu text to speech',
                                                        '/urdu-text-to-speech'),
                                                       ('Hindi text to speech',
                                                        '/hindi-text-to-speech')]},
 'audio-tools-for-youtubers': {'title': 'Audio Tools for YouTubers — Free Online Toolkit | '
                                        'VoxCraft',
                               'meta_description': 'Online audio tools for YouTube: transcribe, '
                                                   'trim, merge, convert, denoise, extract audio '
                                                   'from video. Browser-based, no install.',
                               'eyebrow': 'Creator Toolkit',
                               'h1': 'Audio tools for YouTube creators',
                               'intro': ['Most YouTube jobs don’t need a full DAW. Trim a clip, '
                                         'join narration sections, convert a file, pull audio from '
                                         'a video — small tools handle that without a complicated '
                                         'suite.',
                                         'VoxCraft groups those jobs next to Voice Studio so you '
                                         'can move from generate → clean → export without changing '
                                         'your whole workflow.'],
                               'steps': ['Pick the job you actually need: transcribe, trim, merge, '
                                         'convert, clean, or extract.',
                                         'Keep the original file before destructive edits.',
                                         'Run one tool, review the result, then move on.',
                                         'Export a format your editor accepts.'],
                               'use_cases': [('Narration cleanup',
                                              'Trim and join sections before the timeline.'),
                                             ('Repurposing',
                                              'Transcribe speech into text for notes or captions.'),
                                             ('Format fixes',
                                              'Convert when an editor wants a different file '
                                              'type.')],
                               'faq': [('Which tool first?',
                                        'Start with the problem you have — don’t run every tool on '
                                        'every file.'),
                                       ('Keep the original?',
                                        'Yes, whenever you might redo an edit.'),
                                       ('Are all tools the same?',
                                        'No. Each page lists what it does and current limits.')],
                               'cta_label': 'Open audio tools',
                               'related_links': [('Transcribe audio to text',
                                                  '/tools/transcribe-audio-to-text'),
                                                 ('Trim or cut audio', '/tools/trim-cut-audio'),
                                                 ('Merge audio files', '/tools/merge-audio-files'),
                                                 ('Convert audio format',
                                                  '/tools/convert-audio-format'),
                                                 ('Remove background noise',
                                                  '/tools/remove-background-noise'),
                                                 ('Extract audio from video',
                                                  '/tools/extract-audio-from-video'),
                                                 ('Open Voice Studio', '/studio')]},
 'ai-video-dubbing': {'title': 'AI Video Dubbing Online — Translate & Re-voice | VoxCraft',
                      'meta_description': 'AI video dubbing in the browser: translate and re-voice '
                                          'short clips in English, Hindi, Urdu and more. Free tier '
                                          'available.',
                      'eyebrow': 'Video Redub',
                      'h1': 'AI video dubbing online',
                      'intro': ['Take a spoken clip, translate it, replace the voice track — '
                                'without rebuilding the whole edit. Video Redub runs recognition, '
                                'translation, and neural TTS in the browser, then places audio '
                                'against the original video.',
                                'People use it for short comedy clips, explainers, product demos, '
                                'and regional YouTube versions. Clear source speech works best; '
                                'noisy multi-speaker audio is harder. Always preview before you '
                                'publish.',
                                'Start at <a href="/video-redub">Video Redub</a> or <a '
                                'href="/tools/video-audio-redub">video audio redub</a>. Noisy '
                                'source? Try <a href="/tools/remove-background-noise">denoise</a> '
                                'or <a href="/tools/extract-audio-from-video">extract audio</a> '
                                'first.'],
                      'steps': ['Upload a short video with clear speech (within the size limit).',
                                'Choose source language and target voice language.',
                                'Run redub and wait for the pipeline to finish.',
                                'Preview the dubbed file, download video or audio-only, then '
                                'publish or re-edit.'],
                      'use_cases': [('Regional YouTube',
                                     'Hindi or Urdu versions of an English explainer without '
                                     're-recording.'),
                                    ('Comedy & memes', 'Quick English redubs of regional clips.'),
                                    ('Course drafts', 'Localized narration before hiring talent.')],
                      'faq': [('Is AI video dubbing free?',
                               'Free tier within published limits. See pricing for Pro quotas.'),
                              ('Does it lip-sync faces?',
                               'It times audio windows. Faces are not re-animated.'),
                              ('Which languages work best?',
                               'Clear Hindi, Urdu, and English speech do well; noisy multi-speaker '
                               'audio is harder.'),
                              ('How long should clips be?',
                               'Short creator clips fit the product best — check the tool page for '
                               'current limits.')],
                      'cta_label': 'Open Video Redub',
                      'related_links': [('Video Redub', '/video-redub'),
                                        ('Video audio redub tool', '/tools/video-audio-redub'),
                                        ('Open Voice Studio', '/studio'),
                                        ('Voice cloning', '/voice-cloning'),
                                        ('Extract audio from video',
                                         '/tools/extract-audio-from-video')]},
 'ai-voice-generator': {'title': 'AI Voice Generator Online — Free Neural Voices | VoxCraft',
                        'meta_description': 'Free AI voice generator for creators. Neural TTS in '
                                            'Urdu, Hindi, English and 40+ languages. Download '
                                            'audio — no signup to start.',
                        'eyebrow': 'AI Voice',
                        'h1': 'AI voice generator online',
                        'intro': ['Type a script, pick a neural voice, get spoken audio you can '
                                  'download. Studio covers major creator languages — including '
                                  'solid Urdu and Hindi options — with rate and pitch controls.',
                                  'This isn’t just browser read-aloud. Generate, listen on phone '
                                  'speakers, fix hard words, download for YouTube, courses, or '
                                  'ads.',
                                  'Language pages: <a href="/urdu-text-to-speech">Urdu</a>, <a '
                                  'href="/hindi-text-to-speech">Hindi</a>, <a '
                                  'href="/free-text-to-speech">free TTS</a>. Full list: <a '
                                  'href="/voices">voices</a>.'],
                        'steps': ['Open Voice Studio and pick a language.',
                                  'Preview two or three voices on a line from your real script.',
                                  'Generate a short section first; fix names and numbers.',
                                  'Generate the rest, download, trim or normalize if needed.'],
                        'use_cases': [('YouTube narration', 'Faceless and explainer channels.'),
                                      ('Product demos',
                                       'Consistent product voice without daily recording.'),
                                      ('Multilingual drafts',
                                       'Hear a translation before a human VO session.')],
                        'faq': [('Is the AI voice generator free?',
                                 'Yes within free-tier limits, no account required to start.'),
                                ('Commercial use?',
                                 'Generated audio is usable under current Terms.'),
                                ('Cloning vs stock voices?',
                                 'Stock neural voices are in Studio; cloning is a separate Pro+ '
                                 'workflow.'),
                                ('Which languages?',
                                 'Many, including Urdu and Hindi as first-class options — see '
                                 'Studio.')],
                        'cta_label': 'Generate a voice',
                        'related_links': [('Open Voice Studio', '/studio'),
                                          ('All voices', '/voices'),
                                          ('Free text to speech', '/free-text-to-speech'),
                                          ('Voice cloning', '/voice-cloning'),
                                          ('Urdu text to speech', '/urdu-text-to-speech')]},
 'free-voice-cloning': {'title': 'Voice Cloning Online — Clone a Sample | VoxCraft',
                        'meta_description': 'Voice cloning from a short clean sample for '
                                            'consistent narration. Stock Studio voices on free; '
                                            'cloning on eligible Pro+ plans.',
                        'eyebrow': 'Voice Cloning',
                        'h1': 'Voice cloning online',
                        'intro': ['Upload a short clean sample, build a reusable voice, generate '
                                  'new lines that stay consistent. Cloning is a Pro+ workflow with '
                                  'consent checks. Stock neural voices stay available on free and '
                                  'Pro without cloning.',
                                  'Best results: quiet, single-speaker audio — ideally 30+ seconds '
                                  'of varied speech. Music beds and heavy compression hurt '
                                  'quality.',
                                  'Start at <a href="/voice-cloning">Voice Cloning</a>. For stock '
                                  'voices only, use <a href="/studio">Voice Studio</a>.'],
                        'steps': ['Prepare a clean sample (one speaker, little background noise).',
                                  'Open Voice Cloning and complete any consent steps shown.',
                                  'Upload the sample and create the clone when your plan allows.',
                                  'Generate test lines, then use the clone for longer scripts.'],
                        'use_cases': [('Brand consistency', 'Same host voice across a series.'),
                                      ('Draft vs final',
                                       'Clone for drafts; human record for flagship episodes.'),
                                      ('Series production',
                                       'Reuse a voice without re-recording every episode.')],
                        'faq': [('Is voice cloning free?',
                                 'Studio neural voices are free-tier friendly. Cloning needs an '
                                 'eligible Pro+ plan — see pricing.'),
                                ('Is cloning ethical?',
                                 'Only clone voices you own or have clear permission to use. '
                                 'Consent checks are part of the flow.'),
                                ('How long should the sample be?',
                                 'Clean 30–90 seconds of varied speech beats a noisy 10-second '
                                 'clip.'),
                                ('Can I use Studio TTS voices as a reference?',
                                 'Studio supports using a generated TTS sample as a clone '
                                 'reference in supported flows — see the clone UI.')],
                        'cta_label': 'Open Voice Cloning',
                        'related_links': [('Voice Cloning', '/voice-cloning'),
                                          ('Open Voice Studio', '/studio'),
                                          ('Pricing', '/pricing'),
                                          ('AI voice generator', '/ai-voice-generator')]},
 'marathi-text-to-speech': {'title': 'Marathi Text to Speech Free — AI Voice Online | VoxCraft',
                            'meta_description': 'Free Marathi text to speech online. Devanagari '
                                                'script, neural voices, download for YouTube or '
                                                'lessons — no signup to start.',
                            'eyebrow': 'Marathi TTS',
                            'h1': 'Marathi text to speech (free AI voice)',
                            'intro': ['Marathi narration from text: open Studio, select Marathi, '
                                      'paste Devanagari, generate, download. Free tier without '
                                      'forced signup.',
                                      'Marathi shares Devanagari with Hindi but not the same '
                                      'vocabulary or rhythm. Don’t assume a Hindi script will '
                                      'sound natural as Marathi — test names, city references, and '
                                      'tone on a short sample.',
                                      'Workflow: short test → fix hard words → section generate → '
                                      '<a href="/tools/trim-cut-audio">trim</a> / <a '
                                      'href="/tools/normalize-audio-volume">normalize</a>. '
                                      'Related: <a href="/hindi-text-to-speech">Hindi</a>, <a '
                                      'href="/gujarati-text-to-speech">Gujarati</a>.'],
                            'steps': ['Open Voice Studio and select Marathi when listed.',
                                      'Preview voices on a real line with a name and a number.',
                                      'Generate 20–40 seconds; listen on phone speakers.',
                                      'Revise spellings or rewrite awkward loanwords, then '
                                      'generate the rest.',
                                      'Download and prepare for your editor.'],
                            'use_cases': [('Marathi YouTube',
                                           'Education and product channels for Maharashtra '
                                           'viewers.'),
                                          ('Local business explainers',
                                           'Service videos without hiring VO daily.'),
                                          ('Education', 'Audio versions of written Marathi notes.'),
                                          ('Bilingual publish',
                                           'Marathi track next to Hindi or English.')],
                            'faq': [('Is Marathi TTS free?',
                                     'Yes within free-tier limits; no account required to start.'),
                                    ('Devanagari or Roman?', 'Devanagari is preferred.'),
                                    ('Different from Hindi TTS?',
                                     'Yes — different words and delivery. Preview Marathi on '
                                     'Marathi script.'),
                                    ('Commercial use?', 'Generated audio under current Terms.'),
                                    ('Where is the voice list?', 'Studio language selector.')],
                            'cta_label': 'Try Marathi voices in Studio',
                            'related_links': [('Open Voice Studio', '/studio'),
                                              ('Hindi text to speech', '/hindi-text-to-speech'),
                                              ('Gujarati text to speech',
                                               '/gujarati-text-to-speech'),
                                              ('Free text to speech', '/free-text-to-speech'),
                                              ('Normalize volume',
                                               '/tools/normalize-audio-volume')]},
 'gujarati-text-to-speech': {'title': 'Gujarati Text to Speech Free — AI Voice Online | VoxCraft',
                             'meta_description': 'Free Gujarati text to speech online. Neural '
                                                 'voices for YouTube and business videos — no '
                                                 'signup to start.',
                             'eyebrow': 'Gujarati TTS',
                             'h1': 'Gujarati text to speech (free AI voice)',
                             'intro': ['Gujarati voiceover from written text for YouTube, '
                                       'WhatsApp-first audiences, and regional product videos. Use '
                                       'Gujarati script when you can; test English brand names '
                                       'inside Gujarati lines.',
                                       'Common issues: transliterated place names, mixed '
                                       'Hindi–Gujarati drafts, and long formal sentences. Shorter '
                                       'spoken lines almost always sound better.',
                                       'After export: <a href="/tools/trim-cut-audio">trim</a>, <a '
                                       'href="/tools/merge-audio-files">merge</a>, or <a '
                                       'href="/tools/convert-audio-format">convert</a>. Also <a '
                                       'href="/marathi-text-to-speech">Marathi</a> and <a '
                                       'href="/hindi-text-to-speech">Hindi</a>.'],
                             'steps': ['Open Voice Studio and choose Gujarati when available.',
                                       'Preview on a line from your real niche.',
                                       'Generate a short section first; fix problem words.',
                                       'Produce remaining sections and download.',
                                       'Normalize or trim before publishing.'],
                             'use_cases': [('Gujarati YouTube & Reels',
                                            'Explainers and product demos.'),
                                           ('SME marketing',
                                            'Offer and service videos without daily VO hire.'),
                                           ('Community content',
                                            'Association and diaspora updates.'),
                                           ('Learning',
                                            'Listen-along versions of written material.')],
                             'faq': [('Is Gujarati TTS free?', 'Yes within free-tier limits.'),
                                     ('Gujarati script required?',
                                      'Strongly recommended over pure Roman.'),
                                     ('English product names?',
                                      'Yes — test those lines before a full generate.'),
                                     ('Commercial rights?', 'Follow current Terms.'),
                                     ('Voice list?', 'Live catalog inside Studio.')],
                             'cta_label': 'Open Gujarati voices in Studio',
                             'related_links': [('Open Voice Studio', '/studio'),
                                               ('Hindi text to speech', '/hindi-text-to-speech'),
                                               ('Marathi text to speech',
                                                '/marathi-text-to-speech'),
                                               ('All voices', '/voices'),
                                               ('Free text to speech', '/free-text-to-speech')]},
 'malayalam-text-to-speech': {'title': 'Malayalam Text to Speech Free — AI Voice Online | VoxCraft',
                              'meta_description': 'Free Malayalam text to speech online. Neural '
                                                  'voices for YouTube and education — download '
                                                  'narration, no signup to start.',
                              'eyebrow': 'Malayalam TTS',
                              'h1': 'Malayalam text to speech (free AI voice)',
                              'intro': ['Malayalam narration you can download — not only browser '
                                        'read-aloud. Paste Malayalam script, preview a voice, '
                                        'export for video or courses.',
                                        'Long compounds and proper nouns can stress weaker '
                                        'engines. Keep spoken sentences shorter, and test English '
                                        'tech terms early.',
                                        'Pair with <a href="/tamil-text-to-speech">Tamil TTS</a> '
                                        'for multi-language South Indian audiences. <a '
                                        'href="/tools/normalize-audio-volume">Normalize</a> before '
                                        'upload if needed.'],
                              'steps': ['Open Voice Studio and select Malayalam if listed.',
                                        'Preview two voices on a real script line.',
                                        'Generate a short sample; check names and numbers.',
                                        'Revise, then generate remaining sections.',
                                        'Download and edit as needed.'],
                              'use_cases': [('Malayalam YouTube',
                                             'Explainers, reviews, education.'),
                                            ('Gulf diaspora content',
                                             'Updates for Malayali audiences abroad.'),
                                            ('Courses', 'Audio lessons and revision tracks.'),
                                            ('Product demos',
                                             'Consistent regional product voice.')],
                              'faq': [('Is Malayalam TTS free?',
                                       'Yes within published free-tier limits.'),
                                      ('Native script?', 'Yes — preferred over Romanized input.'),
                                      ('Commercial use?',
                                       'Allowed under current Terms for audio you generate.'),
                                      ('How do I improve quality?',
                                       'Shorter sentences, clear punctuation, section-by-section '
                                       'generation.'),
                                      ('Where are voices listed?', 'Studio language selector.')],
                              'cta_label': 'Try Malayalam voices in Studio',
                              'related_links': [('Open Voice Studio', '/studio'),
                                                ('Tamil text to speech', '/tamil-text-to-speech'),
                                                ('Kannada text to speech',
                                                 '/kannada-text-to-speech'),
                                                ('Free text to speech', '/free-text-to-speech'),
                                                ('Text to speech for YouTube',
                                                 '/text-to-speech-for-youtube')]},
 'kannada-text-to-speech': {'title': 'Kannada Text to Speech Free — AI Voice Online | VoxCraft',
                            'meta_description': 'Free Kannada text to speech online. Neural voices '
                                                'for YouTube and education — no signup to start.',
                            'eyebrow': 'Kannada TTS',
                            'h1': 'Kannada text to speech (free AI voice)',
                            'intro': ['Kannada narration from written text for Karnataka and '
                                      'online Kannada audiences. Generate, test on phone speakers, '
                                      'download for your editor.',
                                      'Test English brand names, mixed Bangalore-style speech, and '
                                      'formal vs casual register. A sample with a price or product '
                                      'line beats a literary demo sentence.',
                                      'After TTS: <a href="/tools/trim-cut-audio">trim</a> and <a '
                                      'href="/tools/normalize-audio-volume">normalize</a>. '
                                      'Related: <a href="/telugu-text-to-speech">Telugu</a>, <a '
                                      'href="/tamil-text-to-speech">Tamil</a>.'],
                            'steps': ['Open Voice Studio and pick Kannada when available.',
                                      'Preview voices on a niche-specific line.',
                                      'Generate a short section; fix problem words.',
                                      'Produce remaining sections labeled by scene.',
                                      'Export and align to video.'],
                            'use_cases': [('Kannada YouTube',
                                           'Tech, education, regional channels.'),
                                          ('Product explainers',
                                           'Kannada stories for local customers.'),
                                          ('Education', 'Course and coaching audio.'),
                                          ('Multi-language South India',
                                           'Kannada alongside Telugu or Tamil.')],
                            'faq': [('Is Kannada TTS free?', 'Yes within free-tier limits.'),
                                    ('Kannada script?', 'Prefer native script over pure Roman.'),
                                    ('Commercial use?', 'Follow live Terms.'),
                                    ('Numbers or brands sound off?',
                                     'Rewrite as words or split the sentence; regenerate that '
                                     'part.'),
                                    ('Need higher limits?',
                                     'See pricing when free caps block you.')],
                            'cta_label': 'Open Kannada voices in Studio',
                            'related_links': [('Open Voice Studio', '/studio'),
                                              ('Telugu text to speech', '/telugu-text-to-speech'),
                                              ('Tamil text to speech', '/tamil-text-to-speech'),
                                              ('All voices', '/voices'),
                                              ('Free text to speech', '/free-text-to-speech')]},
 'remove-noise-from-audio': {'title': 'Remove Noise from Audio Online — Free | VoxCraft',
                             'meta_description': 'Remove background noise from speech online. '
                                                 'Clean podcasts and voiceovers in the browser — '
                                                 'free tier, no install.',
                             'eyebrow': 'Denoise',
                             'h1': 'Remove noise from audio online',
                             'intro': ['Fans, traffic, room hiss — background noise can ruin an '
                                       'otherwise fine take. The denoise tool is aimed at speech '
                                       'so you can salvage interviews, voiceovers, and phone '
                                       'captures.',
                                       'Use <a href="/tools/remove-background-noise">remove '
                                       'background noise</a>. After cleanup, <a '
                                       'href="/tools/normalize-audio-volume">normalize</a> or <a '
                                       'href="/tools/convert-audio-format">convert</a> for your '
                                       'editor.'],
                             'steps': ['Upload a speech-focused clip (music beds are a poor fit).',
                                       'Run denoise and preview.',
                                       'Download, then normalize or trim if needed.'],
                             'use_cases': [('Podcast cleanup',
                                            'Reduce room noise on remote interviews.'),
                                           ('Voiceover salvage', 'Clean a home-recorded take.'),
                                           ('Pre-clone prep',
                                            'Clean a reference sample before cloning.')],
                             'faq': [('Is noise removal free?',
                                      'Yes within free tool limits — see the tool page for size '
                                      'caps.'),
                                     ('Does it work on music?',
                                      'Tuned for speech, not full music mastering.'),
                                     ('File size limit?',
                                      'Check the tool page for the current upload cap.')],
                             'cta_label': 'Remove background noise',
                             'related_links': [('Remove background noise tool',
                                                '/tools/remove-background-noise'),
                                               ('Normalize volume',
                                                '/tools/normalize-audio-volume'),
                                               ('Convert audio', '/tools/convert-audio-format'),
                                               ('Audio tools for YouTubers',
                                                '/audio-tools-for-youtubers'),
                                               ('Open Voice Studio', '/studio')]},
 'text-to-speech-mp3': {'title': 'Text to Speech MP3 Download — Free Online | VoxCraft',
                        'meta_description': 'Convert text to speech and download MP3 online. '
                                            'Neural voices including Urdu and Hindi — free tier, '
                                            'no signup to start.',
                        'eyebrow': 'TTS Download',
                        'h1': 'Text to speech MP3 download',
                        'intro': ['Generate narration and download a file for video editors, LMS '
                                  'uploads, or social posts. Built for export, not only in-browser '
                                  'listening.',
                                  'Start in <a href="/studio">Voice Studio</a>. Need WAV or '
                                  'another format? Use <a '
                                  'href="/tools/convert-audio-format">convert audio format</a>.'],
                        'steps': ['Paste text in Voice Studio and choose a voice.',
                                  'Generate and preview.',
                                  'Download the file; convert format if your editor needs it.'],
                        'use_cases': [('Video editors', 'Drop narration on a timeline.'),
                                      ('Courses', 'Upload lesson audio to an LMS.'),
                                      ('Social clips', 'Short voiceovers for Reels and Shorts.')],
                        'faq': [('Download without signup?', 'Yes on the free tier within limits.'),
                                ('MP3 vs WAV?',
                                 'MP3 is smaller; WAV is higher fidelity. Convert when needed.'),
                                ('Urdu or Hindi MP3?',
                                 'Yes — pick the language in Studio, then download.')],
                        'cta_label': 'Generate and download',
                        'related_links': [('Open Voice Studio', '/studio'),
                                          ('Convert audio format', '/tools/convert-audio-format'),
                                          ('Free text to speech', '/free-text-to-speech'),
                                          ('Urdu text to speech', '/urdu-text-to-speech'),
                                          ('Hindi text to speech', '/hindi-text-to-speech')]}}


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
