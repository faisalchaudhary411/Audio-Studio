"""voices.py — curated neural voice catalogue for VoxCraft.

Primary languages appear first in the Studio dropdown.
Additional languages are available under the same list (with flags)
so the UI stays scannable without a separate crowded panel.
"""

# ISO-style flag emoji per language group (shown in language + voice dropdowns)
LANGUAGE_FLAGS = {
    "US English": "🇺🇸",
    "UK English": "🇬🇧",
    "Australian": "🇦🇺",
    "Indian English": "🇮🇳",
    "Spanish (Spain)": "🇪🇸",
    "Spanish (Mexico)": "🇲🇽",
    "French": "🇫🇷",
    "French (Canada)": "🇨🇦",
    "German": "🇩🇪",
    "Italian": "🇮🇹",
    "Portuguese (Brazil)": "🇧🇷",
    "Portuguese (Portugal)": "🇵🇹",
    "Russian": "🇷🇺",
    "Japanese": "🇯🇵",
    "Korean": "🇰🇷",
    "Chinese (Mandarin)": "🇨🇳",
    "Chinese (Taiwan)": "🇹🇼",
    "Chinese (Hong Kong)": "🇭🇰",
    "Arabic": "🇸🇦",
    "Arabic (Egypt)": "🇪🇬",
    "Hindi": "🇮🇳",
    "Urdu": "🇵🇰",
    "Punjabi": "🇮🇳",
    "Bengali": "🇧🇩",
    "Tamil": "🇮🇳",
    "Telugu": "🇮🇳",
    "Turkish": "🇹🇷",
    "Polish": "🇵🇱",
    "Dutch": "🇳🇱",
    "Swedish": "🇸🇪",
    "Indonesian": "🇮🇩",
    "Malay": "🇲🇾",
    "Thai": "🇹🇭",
    "Vietnamese": "🇻🇳",
    "Czech": "🇨🇿",
    "Danish": "🇩🇰",
    "Finnish": "🇫🇮",
    "Greek": "🇬🇷",
    "Hebrew": "🇮🇱",
    "Hungarian": "🇭🇺",
    "Norwegian": "🇳🇴",
    "Romanian": "🇷🇴",
    "Slovak": "🇸🇰",
    "Ukrainian": "🇺🇦",
    "Filipino": "🇵🇭",
    "Catalan": "🇪🇸",
    "Croatian": "🇭🇷",
    "Bulgarian": "🇧🇬",
}

# Languages shown first in the Studio language dropdown (high demand / core product)
PRIMARY_LANGUAGES = [
    "US English", "UK English", "Indian English", "Australian",
    "Urdu", "Hindi", "Punjabi", "Bengali", "Tamil", "Telugu",
    "Arabic", "Arabic (Egypt)",
    "Spanish (Spain)", "Spanish (Mexico)",
    "French", "French (Canada)", "German", "Italian",
    "Portuguese (Brazil)", "Portuguese (Portugal)",
    "Chinese (Mandarin)", "Japanese", "Korean",
]

VOICES = {
    "US English": {
        "Jenny — Female": "en-US-JennyNeural",
        "Aria — Female": "en-US-AriaNeural",
        "Ava — Female": "en-US-AvaNeural",
        "Emma — Female": "en-US-EmmaNeural",
        "Michelle — Female": "en-US-MichelleNeural",
        "Ana — Female (Child)": "en-US-AnaNeural",
        "Guy — Male": "en-US-GuyNeural",
        "Andrew — Male": "en-US-AndrewNeural",
        "Brian — Male": "en-US-BrianNeural",
        "Christopher — Male": "en-US-ChristopherNeural",
        "Eric — Male": "en-US-EricNeural",
        "Roger — Male": "en-US-RogerNeural",
        "Steffan — Male": "en-US-SteffanNeural",
    },
    "UK English": {
        "Sonia — Female": "en-GB-SoniaNeural",
        "Libby — Female": "en-GB-LibbyNeural",
        "Maisie — Female (Child)": "en-GB-MaisieNeural",
        "Ryan — Male": "en-GB-RyanNeural",
        "Thomas — Male": "en-GB-ThomasNeural",
    },
    "Australian": {
        "Natasha — Female": "en-AU-NatashaNeural",
        "William — Male": "en-AU-WilliamMultilingualNeural",
    },
    "Indian English": {
        "Neerja — Female": "en-IN-NeerjaNeural",
        "Neerja Expressive — Female": "en-IN-NeerjaExpressiveNeural",
        "Prabhat — Male": "en-IN-PrabhatNeural",
    },
    "Urdu": {
        "Uzma — Female": "ur-PK-UzmaNeural",
        "Asad — Male": "ur-PK-AsadNeural",
        "Gul (India) — Female": "ur-IN-GulNeural",
        "Salman (India) — Male": "ur-IN-SalmanNeural",
    },
    "Hindi": {
        "Swara — Female": "hi-IN-SwaraNeural",
        "Madhur — Male": "hi-IN-MadhurNeural",
    },
    # Punjabi neural IDs exist on Azure Speech but are often missing from the
    # free neural endpoint. When they fail, tts_engine falls back to gTTS (`pa`)
    # which has only one generic Punjabi voice (no real male/female choice).
    "Punjabi": {
        "Vaani — Female": "pa-IN-VaaniNeural",
        "Ojas — Male": "pa-IN-OjasNeural",
    },
    "Bengali": {
        "Tanishaa — Female": "bn-IN-TanishaaNeural",
        "Bashkar — Male": "bn-IN-BashkarNeural",
        "Pradeep (Bangladesh) — Male": "bn-BD-PradeepNeural",
        "Nabanita (Bangladesh) — Female": "bn-BD-NabanitaNeural",
    },
    "Tamil": {
        "Pallavi — Female": "ta-IN-PallaviNeural",
        "Valluvar — Male": "ta-IN-ValluvarNeural",
    },
    "Telugu": {
        "Shruti — Female": "te-IN-ShrutiNeural",
        "Mohan — Male": "te-IN-MohanNeural",
    },
    "Arabic": {
        "Zariyah — Female": "ar-SA-ZariyahNeural",
        "Hamed — Male": "ar-SA-HamedNeural",
    },
    "Arabic (Egypt)": {
        "Salma — Female": "ar-EG-SalmaNeural",
        "Shakir — Male": "ar-EG-ShakirNeural",
    },
    "Spanish (Spain)": {
        "Elvira — Female": "es-ES-ElviraNeural",
        "Ximena — Female": "es-ES-XimenaNeural",
        "Alvaro — Male": "es-ES-AlvaroNeural",
    },
    "Spanish (Mexico)": {
        "Dalia — Female": "es-MX-DaliaNeural",
        "Jorge — Male": "es-MX-JorgeNeural",
    },
    "French": {
        "Denise — Female": "fr-FR-DeniseNeural",
        "Eloise — Female (Child)": "fr-FR-EloiseNeural",
        "Henri — Male": "fr-FR-HenriNeural",
    },
    "French (Canada)": {
        "Sylvie — Female": "fr-CA-SylvieNeural",
        "Antoine — Male": "fr-CA-AntoineNeural",
        "Jean — Male": "fr-CA-JeanNeural",
        "Thierry — Male": "fr-CA-ThierryNeural",
    },
    "German": {
        "Katja — Female": "de-DE-KatjaNeural",
        "Amala — Female": "de-DE-AmalaNeural",
        "Seraphina — Female": "de-DE-SeraphinaMultilingualNeural",
        "Conrad — Male": "de-DE-ConradNeural",
        "Killian — Male": "de-DE-KillianNeural",
        "Florian — Male": "de-DE-FlorianMultilingualNeural",
    },
    "Italian": {
        "Elsa — Female": "it-IT-ElsaNeural",
        "Isabella — Female": "it-IT-IsabellaNeural",
        "Diego — Male": "it-IT-DiegoNeural",
        "Giuseppe — Male": "it-IT-GiuseppeMultilingualNeural",
    },
    "Portuguese (Brazil)": {
        "Francisca — Female": "pt-BR-FranciscaNeural",
        "Thalita — Female": "pt-BR-ThalitaMultilingualNeural",
        "Antonio — Male": "pt-BR-AntonioNeural",
    },
    "Portuguese (Portugal)": {
        "Raquel — Female": "pt-PT-RaquelNeural",
        "Duarte — Male": "pt-PT-DuarteNeural",
    },
    "Chinese (Mandarin)": {
        "Xiaoxiao — Female": "zh-CN-XiaoxiaoNeural",
        "Xiaoyi — Female": "zh-CN-XiaoyiNeural",
        "Yunxi — Male": "zh-CN-YunxiNeural",
        "Yunyang — Male": "zh-CN-YunyangNeural",
        "Yunjian — Male": "zh-CN-YunjianNeural",
    },
    "Japanese": {
        "Nanami — Female": "ja-JP-NanamiNeural",
        "Keita — Male": "ja-JP-KeitaNeural",
    },
    "Korean": {
        "SunHi — Female": "ko-KR-SunHiNeural",
        "InJoon — Male": "ko-KR-InJoonNeural",
        "BongJin — Male": "ko-KR-BongJinNeural",
    },
    "Chinese (Taiwan)": {
        "HsiaoChen — Female": "zh-TW-HsiaoChenNeural",
        "HsiaoYu — Female": "zh-TW-HsiaoYuNeural",
        "YunJhe — Male": "zh-TW-YunJheNeural",
    },
    "Chinese (Hong Kong)": {
        "HiuMaan — Female": "zh-HK-HiuMaanNeural",
        "HiuGaai — Female": "zh-HK-HiuGaaiNeural",
        "WanLung — Male": "zh-HK-WanLungNeural",
    },
    "Russian": {
        "Svetlana — Female": "ru-RU-SvetlanaNeural",
        "Dmitry — Male": "ru-RU-DmitryNeural",
    },
    "Turkish": {
        "Emel — Female": "tr-TR-EmelNeural",
        "Ahmet — Male": "tr-TR-AhmetNeural",
    },
    "Polish": {
        "Zofia — Female": "pl-PL-ZofiaNeural",
        "Marek — Male": "pl-PL-MarekNeural",
    },
    "Dutch": {
        "Fenna — Female": "nl-NL-FennaNeural",
        "Colette — Female": "nl-NL-ColetteNeural",
        "Maarten — Male": "nl-NL-MaartenNeural",
    },
    "Swedish": {
        "Sofie — Female": "sv-SE-SofieNeural",
        "Mattias — Male": "sv-SE-MattiasNeural",
    },
    "Indonesian": {
        "Gadis — Female": "id-ID-GadisNeural",
        "Ardi — Male": "id-ID-ArdiNeural",
    },
    "Malay": {
        "Yasmin — Female": "ms-MY-YasminNeural",
        "Osman — Male": "ms-MY-OsmanNeural",
    },
    "Thai": {
        "Premwadee — Female": "th-TH-PremwadeeNeural",
        "Niwat — Male": "th-TH-NiwatNeural",
    },
    "Vietnamese": {
        "HoaiMy — Female": "vi-VN-HoaiMyNeural",
        "NamMinh — Male": "vi-VN-NamMinhNeural",
    },
    "Czech": {
        "Vlasta — Female": "cs-CZ-VlastaNeural",
        "Antonin — Male": "cs-CZ-AntoninNeural",
    },
    "Danish": {
        "Christel — Female": "da-DK-ChristelNeural",
        "Jeppe — Male": "da-DK-JeppeNeural",
    },
    "Finnish": {
        "Noora — Female": "fi-FI-NooraNeural",
        "Harri — Male": "fi-FI-HarriNeural",
    },
    "Greek": {
        "Athina — Female": "el-GR-AthinaNeural",
        "Nestoras — Male": "el-GR-NestorasNeural",
    },
    "Hebrew": {
        "Hila — Female": "he-IL-HilaNeural",
        "Avri — Male": "he-IL-AvriNeural",
    },
    "Hungarian": {
        "Noemi — Female": "hu-HU-NoemiNeural",
        "Tamas — Male": "hu-HU-TamasNeural",
    },
    "Norwegian": {
        "Iselin — Female": "nb-NO-IselinNeural",
        "Finn — Male": "nb-NO-FinnNeural",
    },
    "Romanian": {
        "Alina — Female": "ro-RO-AlinaNeural",
        "Emil — Male": "ro-RO-EmilNeural",
    },
    "Slovak": {
        "Viktoria — Female": "sk-SK-ViktoriaNeural",
        "Lukas — Male": "sk-SK-LukasNeural",
    },
    "Ukrainian": {
        "Polina — Female": "uk-UA-PolinaNeural",
        "Ostap — Male": "uk-UA-OstapNeural",
    },
    "Filipino": {
        "Blessica — Female": "fil-PH-BlessicaNeural",
        "Angelo — Male": "fil-PH-AngeloNeural",
    },
    "Catalan": {
        "Joana — Female": "ca-ES-JoanaNeural",
        "Enric — Male": "ca-ES-EnricNeural",
    },
    "Croatian": {
        "Gabrijela — Female": "hr-HR-GabrijelaNeural",
        "Srecko — Male": "hr-HR-SreckoNeural",
    },
    "Bulgarian": {
        "Kalina — Female": "bg-BG-KalinaNeural",
        "Borislav — Male": "bg-BG-BorislavNeural",
    },
}

FREE_VOICES = {
    "US English": {
        "Jenny — Female": "en-US-JennyNeural",
        "Aria — Female": "en-US-AriaNeural",
        "Guy — Male": "en-US-GuyNeural",
        "Brian — Male": "en-US-BrianNeural",
        "Eric — Male": "en-US-EricNeural",
    },
    "UK English": {
        "Sonia — Female": "en-GB-SoniaNeural",
        "Ryan — Male": "en-GB-RyanNeural",
    },
    "Spanish (Spain)": {
        "Elvira — Female": "es-ES-ElviraNeural",
        "Alvaro — Male": "es-ES-AlvaroNeural",
    },
    "French": {
        "Denise — Female": "fr-FR-DeniseNeural",
        "Henri — Male": "fr-FR-HenriNeural",
    },
    "German": {
        "Katja — Female": "de-DE-KatjaNeural",
        "Conrad — Male": "de-DE-ConradNeural",
    },
    "Japanese": {
        "Nanami — Female": "ja-JP-NanamiNeural",
        "Keita — Male": "ja-JP-KeitaNeural",
    },
    "Arabic": {
        "Zariyah — Female": "ar-SA-ZariyahNeural",
        "Hamed — Male": "ar-SA-HamedNeural",
    },
    "Hindi": {
        "Swara — Female": "hi-IN-SwaraNeural",
        "Madhur — Male": "hi-IN-MadhurNeural",
    },
    "Urdu": {
        "Uzma — Female": "ur-PK-UzmaNeural",
        "Asad — Male": "ur-PK-AsadNeural",
    },
    "Bengali": {
        "Tanishaa — Female": "bn-IN-TanishaaNeural",
        "Bashkar — Male": "bn-IN-BashkarNeural",
    },
    "Tamil": {
        "Pallavi — Female": "ta-IN-PallaviNeural",
        "Valluvar — Male": "ta-IN-ValluvarNeural",
    },
    "Telugu": {
        "Shruti — Female": "te-IN-ShrutiNeural",
        "Mohan — Male": "te-IN-MohanNeural",
    },
}

PREVIEW_TEXT = {
    "US English": "Hi there! This is a voice preview. I hope you like how I sound!",
    "UK English": "Hello! This is a voice preview. I hope you like how I sound!",
    "Australian": "G'day! This is a voice preview. I hope you like how I sound!",
    "Indian English": "Hello! This is a voice preview. I hope you like how I sound!",
    "Spanish (Spain)": "¡Hola! Esta es una vista previa de voz. ¡Espero que te guste!",
    "Spanish (Mexico)": "¡Hola! Esta es una vista previa de voz. ¡Espero que te guste!",
    "French": "Bonjour! Ceci est un aperçu vocal. J'espère que vous aimez ma voix!",
    "French (Canada)": "Bonjour! Ceci est un aperçu vocal.",
    "German": "Hallo! Dies ist eine Sprachvorschau. Ich hoffe, sie gefällt dir!",
    "Italian": "Ciao! Questa è un'anteprima vocale.",
    "Portuguese (Brazil)": "Olá! Esta é uma prévia de voz.",
    "Portuguese (Portugal)": "Olá! Esta é uma pré-visualização de voz.",
    "Russian": "Здравствуйте! Это образец голоса.",
    "Japanese": "こんにちは！これは音声プレビューです。",
    "Korean": "안녕하세요! 음성 미리듣기입니다.",
    "Chinese (Mandarin)": "你好！这是语音预览。",
    "Chinese (Taiwan)": "你好！這是語音預覽。",
    "Chinese (Hong Kong)": "你好！呢個係語音預覽。",
    "Arabic": "مرحبا! هذه معاينة صوتية.",
    "Arabic (Egypt)": "مرحبا! هذه معاينة صوتية.",
    "Hindi": "नमस्ते! यह एक आवाज़ का पूर्वावलोकन है।",
    "Urdu": "ہیلو! یہ ایک آواز کا نمونہ ہے۔",
    "Punjabi": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਇਹ ਆਵਾਜ਼ ਦਾ ਨਮੂਨਾ ਹੈ।",
    "Bengali": "হ্যালো! এটি একটি ভয়েস প্রিভিউ।",
    "Tamil": "வணக்கம்! இது ஒரு குரல் மாதிரி.",
    "Telugu": "నమస్కారం! ఇది వాయిస్ ప్రివ్యూ.",
    "Turkish": "Merhaba! Bu bir ses önizlemesidir.",
    "Polish": "Cześć! To jest podgląd głosu.",
    "Dutch": "Hallo! Dit is een stemvoorbeeld.",
    "Swedish": "Hej! Det här är en röstförhandsvisning.",
    "Indonesian": "Halo! Ini adalah pratinjau suara.",
    "Malay": "Helo! Ini adalah pratonton suara.",
    "Thai": "สวัสดี! นี่คือตัวอย่างเสียง",
    "Vietnamese": "Xin chào! Đây là bản xem trước giọng nói.",
    "Czech": "Ahoj! Toto je ukázka hlasu.",
    "Danish": "Hej! Dette er en stemmeforhåndsvisning.",
    "Finnish": "Hei! Tämä on ääniesikatselu.",
    "Greek": "Γεια σας! Αυτή είναι μια προεπισκόπηση φωνής.",
    "Hebrew": "שלום! זו תצוגה מקדימה של קול.",
    "Hungarian": "Szia! Ez egy hangelőnézet.",
    "Norwegian": "Hei! Dette er en stemmeforhåndsvisning.",
    "Romanian": "Bună! Aceasta este o previzualizare vocală.",
    "Slovak": "Ahoj! Toto je ukážka hlasu.",
    "Ukrainian": "Привіт! Це попередній перегляд голосу.",
    "Filipino": "Kumusta! Ito ay isang preview ng boses.",
    "Catalan": "Hola! Aquesta és una vista prèvia de veu.",
    "Croatian": "Bok! Ovo je pregled glasa.",
    "Bulgarian": "Здравейте! Това е гласова преглед.",
}


def default_preview_text(language: str) -> str:
    return PREVIEW_TEXT.get(language, "Hello! This is a voice preview. I hope you like how I sound!")


def language_label(lang: str) -> str:
    """Display label with flag emoji for dropdowns."""
    flag = LANGUAGE_FLAGS.get(lang, "")
    return f"{flag} {lang}".strip() if flag else lang


def ordered_languages():
    """Primary languages first, then the rest alphabetically."""
    primary = [l for l in PRIMARY_LANGUAGES if l in VOICES]
    rest = sorted(l for l in VOICES if l not in PRIMARY_LANGUAGES)
    return primary + rest


def total_voice_count() -> int:
    return sum(len(v) for v in VOICES.values())


def total_language_count() -> int:
    return len(VOICES)
