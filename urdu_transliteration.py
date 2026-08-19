"""
urdu_transliteration.py — Preprocessing & Transliteration for Roman Urdu & Native Urdu Script.
Converts both Roman Urdu and Perso-Arabic Urdu Script into Devanagari (Hindi) for Chatterbox TTS.
"""

import re

# ── 1. Native Urdu Script (Perso-Arabic) to Devanagari Dictionary ─────────────
URDU_SCRIPT_WORD_MAP = {
    "زندگی": "जिंदगी",
    "ایک": "एक",
    "خاص": "खास",
    "تحفہ": "तोहफा",
    "ہے": "है",
    "ہم": "हम",
    "سب": "सब",
    "کو": "को",
    "خوش": "खुश",
    "ہونا": "होना",
    "چاہیے": "चाहिए",
    "چھوٹی": "छोटी",
    "خوشیاں": "खुशियां",
    "معنی": "मानी",
    "دیتی": "देती",
    "ہیں": "हैं",
    "صبح": "सुबह",
    "جلدی": "जल्दी",
    "اٹھنا": "उठना",
    "اچھی": "अच्छी",
    "عادت": "आदत",
    "اس": "इस",
    "سے": "से",
    "دن": "दिन",
    "اچھا": "अच्छा",
    "بنتا": "बनता",
    "کتابوں": "किताबों",
    "سیکھنا": "सीखना",
    "علم": "इल्म",
    "انسان": "इंसान",
    "طاقت": "ताकत",
    "دیتا": "देता",
    "ہمیشہ": "हमेशा",
    "کچھ": "कुछ",
    "نیا": "नया",
    "ذہن": "ज़हन",
    "کھلتا": "खुलता",
    "کھلا": "खुला",
    "باتیں": "बातें",
    "سمجھتا": "समझता",
    "سمجھ": "समझ",
    "آسان": "आसान",
    "بنتی": "बनती",
    "پسند": "पसंद",
    "دوستی": "दोस्ती",
    "بناتی": "बनाती",
    "دوست": "दोस्त",
    "ساتھ": "साथ",
    "دیتے": "देते",
    "مشکل": "मुश्किल",
    "وقت": "वक्त",
    "میں": "में",
    "ہی": "ही",
    "کام": "काम",
    "آتے": "आते",
    "محبت": "मोहब्बत",
    "خلوص": "खुलूस",
    "دلوں": "दिलों",
    "ملاتی": "मिलाती",
    "لوگوں": "लोगों",
    "مدد": "मदद",
    "دینا": "देना",
    "عمل": "अमल",
    "دل": "दिल",
    "ہوتا": "होता",
    "آتا": "आता",
    "امید": "उम्मीद",
    "آگے": "आगे",
    "لے": "ले",
    "جاتی": "जाती",
    "خواب": "ख्वाब",
    "دیکھنا": "देखना",
    "بات": "बात",
    "خوابوں": "ख्वाबों",
    "سچ": "सच",
    "بنانے": "बनाने",
    "کے": "के",
    "لیے": "लिए",
    "محنت": "मेहनत",
    "کبھی": "कभी",
    "ضائع": "ज़ाया",
    "نہیں": "नहीं",
    "انسانوں": "इंसानों",
    "کوئی": "कोई",
    "نہ": "ना",
    "خاصیت": "खासियत",
    "ہوتی": "होती",
    "اپنے": "अपने",
    "آپ": "आप",
    "یقین": "यकीन",
    "اہم": "अहम",
    "ہمت": "हिम्मत",
    "ملتی": "मिलती",
    "کامیابی": "कामयाबी",
    "مستقل": "मुस्तकिल",
    "مزاجی": "मिजाजी",
    "بھی": "بھی",
    "سوچ": "सोच",
    "مثبت": "मुस्बत",
    "فائدہ": "फ़ायदा",
    "دونوں": "दोनों",
    "حالتوں": "हालतों",
    "سکون": "सुकून",
    "فیصلے": "फैसले",
    "ہوتے": "होते",
    "مستقبل": "मुस्तक़बिल",
    "آج": "आज",
    "کل": "کل",
    "کا": "का",
    "پھل": "फल",
    "یہ": "यह",
    "سچائی": "सच्चाई",
    "معلوم": "मालूम",
    "ہونی": "होनी",
    "اور": "और",
    "ساتھی": "साथी",
    "تعلیم": "तालीम",
    "نعمت": "नेमत",
    "استاد": "उस्ताद",
    "طالب": "तालिब",
    "علموں": "इल्मों",
    "بدل": "बदल",
    "تنہا": "तन्हा",
    "نیکی": "नेकी",
    "بدلہ": "बदला",
    "خدمت": "खिदमत",
    "لوگ": "लोग",
    "بناتے": "बनाते",
    "اچھائی": "अच्छाई",
    "ملتے": "मिलते",
    "نیکیاں": "नेकियां",
    "خوشی": "खुशी",
}

# Aspirated Digraph replacements for Fallback transliteration
URDU_DIGRAPHS = {
    "بھ": "भ", "پھ": "फ", "تھ": "थ", "ٹھ": "ठ", "جھ": "झ",
    "چھ": "छ", "دھ": "ध", "ڈھ": "ढ", "کھ": "ख", "گھ": "घ",
}

# Fallback character mapping for out-of-vocabulary Urdu words
URDU_CHAR_MAP = {
    "ا": "अ", "آ": "आ", "ب": "ब", "پ": "प", "ت": "त", "ٹ": "ट", "ث": "स",
    "ج": "ज", "چ": "च", "ح": "ह", "خ": "ख़", "د": "द", "ڈ": "ड", "ذ": "ज़",
    "ر": "र", "ڑ": "ड़", "ز": "ज़", "ژ": "झ़", "س": "स", "ش": "श", "ص": "स",
    "ض": "ज़", "ط": "त", "ظ": "ज़", "ع": "अ", "غ": "ग़", "ف": "फ़", "ق": "क़",
    "ک": "क", "گ": "ग", "ل": "ल", "م": "म", "ن": "न", "ں": "ं", "و": "व",
    "ہ": "ह", "ھ": "ह", "ی": "य", "ے": "ए", "۔": "।", "؟": "?", "ئ": "इ",
}

# ── 2. Roman Urdu Fixes & Devanagari Mapping ─────────────────────────────────
ROMAN_URDU_FIXES = {
    r"\bditi\b": "deti", r"\bdiiti\b": "deti", r"\bdita\b": "deta",
    r"\bmalti\b": "milti", r"\bmalte\b": "milte", r"\batna\b": "uthna",
    r"\bsaba\b": "subah", r"\bdan\b": "din", r"\bnia\b": "naya",
    r"\bkhalta\b": "khulta", r"\bpasan\b": "pasand", r"\bmusabbat\b": "musbat",
    r"\bmustabdil\b": "mustaqbil", r"\bkhulus\b": "khuluus", r"\bkhab\b": "khwab",
}

ROMAN_TO_DEVANAGARI_WORDS = {
    "zindagi": "जिंदगी", "khas": "खास", "khaas": "खास", "tohfa": "तोहफा",
    "hum": "हम", "sab": "सब", "ko": "को", "khush": "खुश", "hona": "होना",
    "chahiye": "चाहिए", "chhoti": "छोटी", "khushiyan": "खुशियां", "maani": "मानी",
    "deti": "देती", "deta": "देता", "hain": "हैं", "hai": "है", "subah": "सुबह",
    "jaldi": "जल्दी", "uthna": "उठना", "ek": "एक", "achhi": "अच्छी", "achha": "अच्छा",
    "aadat": "आदत", "is": "इस", "se": "से", "din": "दिन", "banta": "बनता",
    "kitabon": "किताबों", "ilm": "इल्म", "insan": "इंसान", "taakat": "ताकत", "hamesha": "हमेशा",
    "kuch": "कुछ", "naya": "नया", "seekhna": "सीखना", "jahan": "जहां",
    "khulta": "खुलता", "khula": "खुला", "nayi": "नयी", "baatein": "बातें",
    "samajhta": "समझता", "samajh": "समझ", "aasan": "आसान", "banti": "बनती",
    "pasand": "पसंद", "dosti": "दोस्ती", "banati": "बनाती", "dost": "दोस्त",
    "saath": "साथ", "dete": "देते", "mushkil": "मुश्किल", "waqt": "वक्त",
    "mein": "में", "hi": "ही", "kaam": "काम", "aate": "आते", "mohabbat": "मोहब्बत",
    "khuluus": "खुलूस", "dilon": "दिलों", "milati": "मिलाती", "logon": "लोगों",
    "madad": "मदद", "dena": "देना", "amal": "अमल", "dil": "दिल", "hota": "होता",
    "aata": "आता", "umeed": "उम्मीद", "aage": "आगे", "le": "ले", "jaati": "जाती",
    "khwab": "ख्वाब", "dekhna": "देखना", "baat": "बात", "khwabon": "ख्वाबों",
    "sach": "सच", "banane": "बनाने", "ke": "के", "liye": "लिए", "mehnat": "मेहनत",
    "kabhi": "कभी", "zaya": "जाया", "nahi": "नहीं", "insanon": "इंसानों",
    "koi": "कोई", "na": "ना", "khasiyat": "खासियत", "hoti": "होती", "apne": "अपने",
    "aap": "आप", "yakeen": "यकीन", "ahem": "अहम", "himmat": "हिम्मत",
    "milti": "मिलती", "kaamyabi": "कामयाबी", "mustaqil": "मुस्तकिल",
    "mizaji": "मिजाजी", "bhi": "भी", "soch": "सोच", "musbat": "मुस्बत",
    "fayda": "फ़ायदा", "dono": "दोनों", "halaton": "हालतों", "sukoon": "सुकून",
    "faisle": "फैसले", "hote": "होते", "mustaqbil": "मुस्तक़बिल", "aaj": "आज",
    "kal": "कल", "ka": "का", "phal": "फल", "yeh": "यह", "sachai": "सच्चाई",
    "maloom": "मालूम", "honi": "होनी", "aur": "और", "sathi": "साथी",
    "taleem": "तालीम", "neemat": "नेमत", "ustad": "उस्ताद", "talib": "तालिब",
    "e": "ए", "ilmon": "इल्मों", "talib-e-ilmon": "तालिब-ए-इल्मों",
    "badal": "बदल", "seekhne": "सीखने", "wala": "वाला", "tanha": "तन्हा",
    "neki": "नेकी", "badla": "बदला", "khidmat": "ख़िदमत", "log": "लोग",
    "banate": "बनाते", "achhai": "अच्छाई", "milte": "मिलते", "nekiyan": "नेकियां",
    "khushi": "खुशी",
}


def transliterate_urdu_script_to_devanagari(text: str) -> str:
    """Converts native Urdu Perso-Arabic text to Devanagari."""
    tokens = re.split(r"(\s+|[.,!?۔؟।—-])", text)
    result = []
    for token in tokens:
        clean_token = token.strip()
        if clean_token in URDU_SCRIPT_WORD_MAP:
            result.append(URDU_SCRIPT_WORD_MAP[clean_token])
        elif clean_token:
            # First replace aspirated digraphs (e.g. کھ -> ख)
            word = token
            for digraph, dev_char in URDU_DIGRAPHS.items():
                word = word.replace(digraph, dev_char)
            # Fallback character conversion
            char_converted = "".join(URDU_CHAR_MAP.get(ch, ch) for ch in word)
            result.append(char_converted)
        else:
            result.append(token)
    return "".join(result)


def fix_roman_urdu_misspellings(text: str) -> str:
    cleaned_text = text
    for pattern, replacement in ROMAN_URDU_FIXES.items():
        cleaned_text = re.sub(pattern, replacement, cleaned_text, flags=re.IGNORECASE)
    return cleaned_text


def transliterate_roman_to_devanagari(text: str) -> str:
    tokens = re.split(r"(\s+|[.,!?۔؟।])", text)
    result = []
    for token in tokens:
        lower_token = token.lower().strip()
        if lower_token in ROMAN_TO_DEVANAGARI_WORDS:
            result.append(ROMAN_TO_DEVANAGARI_WORDS[lower_token])
        else:
            result.append(token)
    return "".join(result)


def prepare_text_for_tts(text: str) -> tuple[str, str]:
    """
    Main entry point for clone_engine.py.
    Transliterates both Native Urdu script and Roman Urdu to Devanagari.
    """
    if not text or not text.strip():
        return "", "en"

    # Check for native Urdu Perso-Arabic script (\u0600-\u06FF)
    has_urdu_script = bool(re.search(r"[\u0600-\u06FF]", text))
    if has_urdu_script:
        devanagari_text = transliterate_urdu_script_to_devanagari(text.strip())
        return devanagari_text, "hi"

    # Process Roman Urdu text
    cleaned_text = fix_roman_urdu_misspellings(text)
    devanagari_text = transliterate_roman_to_devanagari(cleaned_text)

    return devanagari_text.strip(), "hi"
