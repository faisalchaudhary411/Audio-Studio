"""voices.py — voice catalogue, ported directly from the Streamlit app."""

VOICES = {
    "US English": {
        "Jenny — Female": "en-US-JennyNeural", "Aria — Female": "en-US-AriaNeural",
        "Ava — Female": "en-US-AvaNeural", "Emma — Female": "en-US-EmmaNeural",
        "Michelle — Female": "en-US-MichelleNeural", "Ana — Female (Child)": "en-US-AnaNeural",
        "Guy — Male": "en-US-GuyNeural", "Andrew — Male": "en-US-AndrewNeural",
        "Brian — Male": "en-US-BrianNeural", "Christopher — Male": "en-US-ChristopherNeural",
        "Eric — Male": "en-US-EricNeural", "Roger — Male": "en-US-RogerNeural",
        "Steffan — Male": "en-US-SteffanNeural",
    },
    "UK English": {
        "Sonia — Female": "en-GB-SoniaNeural", "Libby — Female": "en-GB-LibbyNeural",
        "Maisie — Female (Child)": "en-GB-MaisieNeural", "Ryan — Male": "en-GB-RyanNeural",
        "Thomas — Male": "en-GB-ThomasNeural",
    },
    "Australian": {
        "Natasha — Female": "en-AU-NatashaNeural",
        "William — Male": "en-AU-WilliamMultilingualNeural",
    },
    "Indian English": {
        "Neerja — Female": "en-IN-NeerjaNeural", "Neerja Expressive — Female": "en-IN-NeerjaExpressiveNeural",
        "Prabhat — Male": "en-IN-PrabhatNeural",
    },
    "Spanish (Spain)": {"Elvira — Female": "es-ES-ElviraNeural", "Ximena — Female": "es-ES-XimenaNeural", "Alvaro — Male": "es-ES-AlvaroNeural"},
    "Spanish (Mexico)": {"Dalia — Female": "es-MX-DaliaNeural", "Jorge — Male": "es-MX-JorgeNeural"},
    "French": {"Denise — Female": "fr-FR-DeniseNeural", "Eloise — Female (Child)": "fr-FR-EloiseNeural", "Henri — Male": "fr-FR-HenriNeural"},
    "French (Canada)": {"Sylvie — Female": "fr-CA-SylvieNeural", "Antoine — Male": "fr-CA-AntoineNeural", "Jean — Male": "fr-CA-JeanNeural", "Thierry — Male": "fr-CA-ThierryNeural"},
    "German": {"Katja — Female": "de-DE-KatjaNeural", "Amala — Female": "de-DE-AmalaNeural", "Seraphina — Female": "de-DE-SeraphinaMultilingualNeural", "Conrad — Male": "de-DE-ConradNeural", "Killian — Male": "de-DE-KillianNeural", "Florian — Male": "de-DE-FlorianMultilingualNeural"},
    "Italian": {"Elsa — Female": "it-IT-ElsaNeural", "Isabella — Female": "it-IT-IsabellaNeural", "Diego — Male": "it-IT-DiegoNeural", "Giuseppe — Male": "it-IT-GiuseppeMultilingualNeural"},
    "Portuguese (Brazil)": {"Francisca — Female": "pt-BR-FranciscaNeural", "Thalita — Female": "pt-BR-ThalitaMultilingualNeural", "Antonio — Male": "pt-BR-AntonioNeural"},
    "Portuguese (Portugal)": {"Raquel — Female": "pt-PT-RaquelNeural", "Duarte — Male": "pt-PT-DuarteNeural"},
    "Russian": {"Svetlana — Female": "ru-RU-SvetlanaNeural", "Dmitry — Male": "ru-RU-DmitryNeural"},
    "Japanese": {"Nanami — Female": "ja-JP-NanamiNeural", "Keita — Male": "ja-JP-KeitaNeural"},
    "Korean": {"Sun-Hi — Female": "ko-KR-SunHiNeural", "InJoon — Male": "ko-KR-InJoonNeural", "Hyunsu — Male": "ko-KR-HyunsuMultilingualNeural"},
    "Chinese (Mandarin)": {"Xiaoxiao — Female": "zh-CN-XiaoxiaoNeural", "Xiaoyi — Female": "zh-CN-XiaoyiNeural", "Yunxi — Male": "zh-CN-YunxiNeural", "Yunyang — Male": "zh-CN-YunyangNeural", "Yunjian — Male": "zh-CN-YunjianNeural"},
    "Arabic": {"Zariyah — Female": "ar-SA-ZariyahNeural", "Hamed — Male": "ar-SA-HamedNeural"},
    "Hindi": {"Swara — Female": "hi-IN-SwaraNeural", "Madhur — Male": "hi-IN-MadhurNeural"},
    "Turkish": {"Emel — Female": "tr-TR-EmelNeural", "Ahmet — Male": "tr-TR-AhmetNeural"},
    "Polish": {"Zofia — Female": "pl-PL-ZofiaNeural", "Marek — Male": "pl-PL-MarekNeural"},
    "Dutch": {"Fenna — Female": "nl-NL-FennaNeural", "Colette — Female": "nl-NL-ColetteNeural", "Maarten — Male": "nl-NL-MaartenNeural"},
    "Swedish": {"Sofie — Female": "sv-SE-SofieNeural", "Mattias — Male": "sv-SE-MattiasNeural"},
    "Urdu": {"Uzma — Female": "ur-PK-UzmaNeural", "Asad — Male": "ur-PK-AsadNeural", "Gul (India) — Female": "ur-IN-GulNeural", "Salman (India) — Male": "ur-IN-SalmanNeural"},
    "Punjabi": {"Vaani — Female": "pa-IN-VaaniNeural", "Ojas — Male": "pa-IN-OjasNeural"},
    # Note: "More Languages (Google, 1 voice each)" (GT:: prefixed) intentionally
    # left out of this pass — those route through gTTS directly rather than
    # edge-tts and need a small extra branch in tts_dispatch. Flag if you want
    # those wired back in.
}

FREE_VOICES = {
    "US English": {"Jenny — Female": "en-US-JennyNeural", "Aria — Female": "en-US-AriaNeural", "Guy — Male": "en-US-GuyNeural", "Brian — Male": "en-US-BrianNeural", "Eric — Male": "en-US-EricNeural"},
    "UK English": {"Sonia — Female": "en-GB-SoniaNeural", "Ryan — Male": "en-GB-RyanNeural"},
    "Spanish (Spain)": {"Elvira — Female": "es-ES-ElviraNeural", "Alvaro — Male": "es-ES-AlvaroNeural"},
    "French": {"Denise — Female": "fr-FR-DeniseNeural", "Henri — Male": "fr-FR-HenriNeural"},
    "German": {"Katja — Female": "de-DE-KatjaNeural", "Conrad — Male": "de-DE-ConradNeural"},
    "Japanese": {"Nanami — Female": "ja-JP-NanamiNeural", "Keita — Male": "ja-JP-KeitaNeural"},
    "Arabic": {"Zariyah — Female": "ar-SA-ZariyahNeural", "Hamed — Male": "ar-SA-HamedNeural"},
    "Hindi": {"Swara — Female": "hi-IN-SwaraNeural", "Madhur — Male": "hi-IN-MadhurNeural"},
    "Urdu": {"Uzma — Female": "ur-PK-UzmaNeural", "Asad — Male": "ur-PK-AsadNeural"},
}

PREVIEW_TEXT = {
    "US English": "Hi there! This is a voice preview. I hope you like how I sound!",
    "UK English": "Hello! This is a voice preview. I hope you like how I sound!",
    "Australian": "G'day! This is a voice preview. I hope you like how I sound!",
    "Indian English": "Hello! This is a voice preview. I hope you like how I sound!",
    "Spanish (Spain)": "¡Hola! Esta es una vista previa de voz. ¡Espero que te guste!",
    "Spanish (Mexico)": "¡Hola! Esta es una vista previa de voz. ¡Espero que te guste!",
    "French": "Bonjour! Ceci est un aperçu vocal. J'espère que vous aimez ma voix!",
    "German": "Hallo! Dies ist eine Sprachvorschau. Ich hoffe, sie gefällt dir!",
    "Urdu": "ہیلو! یہ ایک آواز کا نمونہ ہے۔",
    "Hindi": "नमस्ते! यह एक आवाज़ का पूर्वावलोकन है।",
    "Arabic": "مرحبا! هذه معاينة صوتية.",
    "Japanese": "こんにちは！これは音声プレビューです。",
}


def default_preview_text(language: str) -> str:
    return PREVIEW_TEXT.get(language, "Hello! This is a voice preview. I hope you like how I sound!")
