"""
urdu_transliteration.py — Universal Transliteration for Roman Urdu & Native Urdu Script.
Converts any Urdu input (Dictionary matched or OOV) into clean Devanagari for Chatterbox TTS.
"""

import re

# ── 1. Native Urdu Script (Perso-Arabic) Mappings ──────────────────────────────
URDU_SCRIPT_WORD_MAP = {
    # Function Words & Possessives
    "کی": "की", "کا": "का", "کے": "के", "کو": "को", "میں": "में", "سے": "से",
    "پر": "पर", "بھی": "भी", "کل": "कल", "یہ": "यह", "وہ": "वह", "تھا": "था",
    "تھی": "थी", "تھے": "थे", "ہے": "है", "ہیں": "हैं", "ہو": "हो", "ہونا": "होना",
    "چاہیے": "चाहिए", "نہ": "ना", "لیکن": "लेकिन", "جس": "जिस", "موڑ": "मोड़",
    "سبق": "सबक़", "راستے": "रास्ते", "مشکلات": "मुश्किलात", "سامنے": "सामने",

    # Vocabulary Mappings
    "زندگی": "ज़िंदगी", "ایک": "एक", "خاص": "खास", "تحفہ": "तोहफा", "ہم": "हम",
    "سب": "सब", "خوش": "खुश", "چھوٹی": "छोटी", "خوشیاں": "खुशियां", "معنی": "मानी",
    "دیتی": "देती", "صبح": "सुबह", "جلدی": "जल्दी", "اٹھنا": "उठना", "اچھی": "अच्छी",
    "اچھا": "अच्छा", "اچھے": "अच्छे", "عادت": "आदत", "اس": "इस", "دن": "दिन",
    "بنتا": "बनता", "کتابوں": "किताबों", "سیکھنا": "सीखना", "سیکھنے": "सीखने",
    "علم": "इल्म", "انسان": "इंसान", "طاقت": "ताकत", "دیتا": "देता", "ہمیشہ": "हमेशा",
    "کچھ": "कुछ", "نیا": "नया", "نئی": "नयी", "ذہن": "ज़हन", "کھلتا": "खुलता",
    "کھلا": "खुला", "باتیں": "बातें", "سمجھتا": "समझता", "سمجھ": "समझ",
    "آسان": "आसान", "بنتی": "बनती", "پسند": "पसंद", "دوستی": "दोस्ती",
    "بناتی": "बनाती", "دوست": "दोस्त", "ساتھ": "साथ", "دیتے": "देते",
    "مشکل": "मुश्किल", "وقت": "वक्त", "ہی": "ही", "کام": "काम", "آتے": "आते",
    "محبت": "मोहब्बत", "خلوص": "ख़ुलूस", "دلوں": "दिलों", "ملاتی": "मिलाती",
    "لوگوں": "लोगों", "مدد": "मदद", "دینا": "देना", "عمل": "अमल", "دل": "दिल",
    "ہوتا": "होता", "آتا": "آتا", "امید": "उम्मीद", "آگے": "आगे", "لے": "ले",
    "جاتی": "जाती", "خواب": "ख्वाब", "دیکھنا": "देखना", "بات": "बात",
    "خوابوں": "ख्वाबों", "سچ": "सच", "بنانے": "बनाने", "محنت": "मेहनत",
    "کبھی": "कभी", "ضائع": "ज़ाया", "نہیں": "नहीं", "انسانوں": "इंसानों",
    "کوئی": "कोई", "خاصیت": "खासियत", "ہوتی": "होती", "اپنے": "अपने",
    "آپ": "आप", "یقین": "यकीन", "اہم": "अहम", "ہمت": "हिम्मत", "ملتی": "मिलती",
    "ملتا": "मिलता", "کامیابی": "कामयाबी", "مستقل": "मुस्तकिल", "مزاجی": "मिज़ाजी",
    "سوچ": "सोच", "مثبت": "मुस्बत", "فائدہ": "फ़ायदा", "دونوں": "दोनों",
    "حالتوں": "हालतों", "سکون": "सुकून", "فیصلے": "फैसले", "ہوتے": "ہوتے",
    "مستقبل": "मुस्तक़बिल", "آج": "आज", "پھل": "फल", "سچائی": "سच्चाई",
    "معلوم": "मालूम", "ہونی": "होनी", "اور": "और", "ساتھی": "साथी",
    "تعلیم": "तालीम", "نعمت": "नेमत", "استاد": "उस्ताद", "طالب": "तालिब",
    "علموں": "इल्मों", "بدل": "बदल", "تنہا": "तन्हा", "نیکی": "नेकी",
    "بدلہ": "बदला", "خدمت": "ख़िदमत", "لوگ": "लोग", "بناتے": "बनाते",
    "اچھائی": "अच्छाई", "ملتے": "मिलते", "نیکیاں": "नेकियां", "خوشی": "खुशी",
    "بڑھاتا": "बढ़ाता", "والا": "वाला"
}

URDU_DIGRAPHS = {
    "بھ": "भ", "پھ": "फ", "تھ": "थ", "ٹھ": "ठ", "جھ": "झ",
    "چھ": "छ", "دھ": "ध", "ڈھ": "ढ", "کھ": "ख", "گھ": "घ"
}

URDU_CHAR_MAP = {
    "ا": "अ", "آ": "आ", "ب": "ब", "پ": "پ", "ت": "त", "ٹ": "ट", "ث": "स",
    "ج": "ज", "چ": "च", "ح": "ह", "خ": "ख़", "د": "द", "ڈ": "ड", "ذ": "ज़",
    "ر": "र", "ڑ": "ड़", "ز": "ज़", "ژ": "झ़", "س": "स", "ش": "श", "ص": "स",
    "ض": "ज़", "ط": "त", "ظ": "ज़", "ع": "अ", "غ": "ग़", "ف": "फ़", "ق": "क़",
    "ک": "क", "گ": "ग", "ل": "ल", "م": "म", "ن": "न", "ں": "ं", "و": "व",
    "ہ": "ह", "ھ": "ह", "ی": "य", "ے": "ए", "۔": "।", "؟": "?", "ئ": "इ"
}

# ── 2. Roman Urdu Dictionary & Fixes ──────────────────────────────────────────
ROMAN_URDU_FIXES = {
    r"\bditi\b": "deti", r"\bdiiti\b": "deti", r"\bdita\b": "deta",
    r"\bmalti\b": "milti", r"\bmalte\b": "milte", r"\batna\b": "uthna",
    r"\bsaba\b": "subah", r"\bdan\b": "din", r"\bnia\b": "naya",
    r"\bkhalta\b": "khulta", r"\bpasan\b": "pasand", r"\bmusabbat\b": "musbat",
    r"\bmustabdil\b": "mustaqbil", r"\bkhulus\b": "khuluus", r"\bkhab\b": "khwab",
    r"\bmeni\b": "maani", r"\blaye\b": "liye", r"\bya\b": "yeh",
    r"\balam\b": "ilm", r"\bamed\b": "umeed", r"\bsathi\b": "saathi",
    r"\bkhushiya\b": "khushiyan", r"\bnekiya\b": "nekiyan", r"\bnai\b": "nayi",
    r"\bkhwabo\b": "khwabon", r"\bkitabo\b": "kitabon", r"\bdilo\b": "dilon",
    r"\blogo\b": "logon", r"\binsano\b": "insanon", r"\bhalato\b": "halaton",
    r"\bkyun\b": "kyun", r"\bkyunk\b": "kyunke", r"\bkyunke\b": "kyunke",
    r"\blekan\b": "lekin", r"\bjas\b": "jis", r"\bmawar\b": "mor",
    r"\bmowar\b": "mor", r"\braste\b": "raste", r"\bmuskl\b": "mushkil",
    r"\bkhas\b": "khaas"
}

ROMAN_TO_DEVANAGARI_WORDS = {
    "ki": "कि", "ka": "का", "ke": "के", "ko": "को", "bhi": "भी", "kal": "कल",
    "zindagi": "ज़िंदगी", "khas": "खास", "khaas": "खास", "tohfa": "तोहफा",
    "hum": "हम", "sab": "सब", "khush": "खुश", "hona": "होना", "chahiye": "चाहिए",
    "chhoti": "छोटी", "khushiyan": "खुशियां", "maani": "मानी", "deti": "देती",
    "deta": "देता", "hain": "हैं", "hai": "है", "subah": "सुबह", "jaldi": "जल्दी",
    "uthna": "उठना", "ek": "एक", "achhi": "अच्छी", "achha": "अच्छा", "achhe": "अच्छे",
    "aadat": "आदत", "is": "इस", "se": "से", "din": "दिन", "banta": "बनता",
    "kitabon": "किताबों", "ilm": "इल्म", "insan": "इंसान", "taakat": "ताकत",
    "hamesha": "हमेशा", "kuch": "कुछ", "naya": "نया", "nayi": "नयी",
    "seekhna": "सीखना", "seekhne": "सीखने", "jahan": "जहां", "khulta": "खुलता",
    "khula": "खुला", "baatein": "बातें", "samajhta": "समझता", "samajh": "समझ",
    "aasan": "आसान", "banti": "बनती", "pasand": "पसंद", "dosti": "दोस्ती",
    "banati": "बनाती", "dost": "दोस्त", "saath": "साथ", "dete": "देते",
    "mushkil": "मुश्किल", "waqt": "वक्त", "mein": "में", "hi": "ही", "kaam": "काम",
    "aate": "आते", "mohabbat": "मोहब्बत", "khuluus": "ख़ुलूस", "dilon": "दिलों",
    "milati": "मिलाती", "logon": "लोगों", "madad": "मदद", "dena": "देना",
    "amal": "अमल", "dil": "दिल", "hota": "होता", "aata": "आता", "umeed": "उम्मीद",
    "aage": "आगे", "le": "ले", "jaati": "जाती", "khwab": "ख्वाब", "dekhna": "देखना",
    "baat": "बात", "khwabon": "ख्वाबों", "sach": "सच", "banane": "बनाने",
    "liye": "लिए", "mehnat": "मेहनत", "kabhi": "कभी", "zaya": "ज़ाया",
    "nahi": "नहीं", "insanon": "इंसानों", "koi": "कोई", "na": "ना",
    "khasiyat": "खासियत", "hoti": "होती", "apne": "अपने", "aap": "आप",
    "yakeen": "यकीन", "ahem": "अहम", "himmat": "हिम्मत", "milti": "मिलती",
    "milta": "मिलता", "kaamyabi": "कामयाबी", "mustaqil": "मुस्तकिल",
    "mizaji": "मिज़ाजी", "soch": "सोच", "musbat": "मुस्बत", "fayda": "फ़ायदा",
    "dono": "दोनों", "halaton": "हालतों", "sukoon": "सुकून", "faisle": "फैसले",
    "hote": "होते", "mustaqbil": "मुस्तक़बिल", "aaj": "आज", "phal": "फल",
    "yeh": "यह", "sachai": "सच्चाई", "maloom": "मालूम", "honi": "होनी",
    "aur": "और", "saathi": "साथी", "taleem": "तालीम", "neemat": "नेमत",
    "ustad": "उस्ताद", "talib": "तालिब", "e": "ए", "ilmon": "इल्मों",
    "badal": "बदल", "wala": "वाला", "tanha": "तन्हा", "neki": "नेकी",
    "badla": "बदला", "khidmat": "ख़िदمت", "log": "लोग", "banate": "बनाते",
    "achhai": "अच्छाई", "milte": "मिलते", "nekiyan": "नेकियां", "khushi": "खुशी",
    "barhata": "बढ़ाता", "safar": "सफ़र", "jis": "जिस", "mor": "मोड़",
    "sabaq": "सबक़", "raste": "रास्ते", "mushkilat": "मुश्किलात", "samne": "सामने",
    "lekin": "लेकिन", "haal": "हाल", "kiran": "किरण", "roshni": "रोशनी",
    "bikherte": "बिखेरती", "bikhertee": "बिखेरती", "to": "तो", "hameen": "हमें",
    "hamein": "हमें", "yaad": "याद", "dilati": "दिलाती", "mauqa": "मौका",
    "aati": "आती", "doston": "दोस्तों", "suhbat": "सोहबत", "buzurgon": "बुज़ुर्गों",
    "izzat": "इज़्ज़त", "karna": "करना", "mayno": "मायनों", "insaniyat": "इंसानियत",
    "jodne": "जोड़ने", "kisi": "किसी", "sakte": "सकते", "zaroor": "ज़रूर",
    "karen": "करें", "kyunke": "क्योंकि", "khubsurat": "खूबसूरत", "zaroori": "ज़रूरी",
    "raat": "रात", "ghabrana": "घबराना", "andheri": "अंधेरी", "baad": "बाद",
    "roshan": "रोशन", "rakhein": "रखिए", "khud": "खुद", "bharosa": "भरोसा",
    "duniya": "दुनिया", "rok": "रोक", "mil": "मिल", "rahein": "रहें",
    "akela": "अकेला", "thak": "थक", "jaata": "जाता", "koshish": "कोशिश",
    "khazana": "ख़ज़ाना", "baantne": "बांटने", "shukr": "शुक्र", "ada": "अदा"
}


def fallback_roman_to_devanagari(word: str) -> str:
    """
    Robust phoneme-tokenizing transliteration engine for OOV Roman Urdu words.
    Attaches Devanagari Matras (vowel diacritics) to preceding consonants
    instead of emitting independent vowel characters.
    """
    w = word.lower().strip()
    if not w:
        return ""

    CONSONANT_MAP = [
        ("kh", "ख़"), ("gh", "گ़"), ("sh", "श"), ("ch", "च"),
        ("jh", "झ"), ("bh", "भ"), ("ph", "फ़"), ("th", "थ"),
        ("dh", "ध"), ("rh", "ढ़"), ("zh", "झ़"), ("ck", "क"),
        ("b", "ब"), ("c", "क"), ("d", "द"), ("f", "फ़"), ("g", "ग"),
        ("h", "ह"), ("j", "ज"), ("k", "क"), ("l", "ल"), ("m", "म"),
        ("n", "न"), ("p", "प"), ("q", "क़"), ("r", "र"), ("s", "स"),
        ("t", "त"), ("v", "व"), ("w", "व"), ("x", "क्स"), ("y", "य"), ("z", "ज़")
    ]

    # Vowels: (roman, independent_char, matra_char)
    VOWEL_MAP = [
        ("ein", "एं", "ें"), ("aan", "आन", "ां"), ("oon", "ऊं", "ूं"), ("on", "ओं", "ों"),
        ("aai", "आई", "ाई"), ("aau", "आऊ", "ाऊ"),
        ("aa", "आ", "ा"), ("ee", "ई", "ी"), ("oo", "ऊ", "ू"),
        ("ai", "ऐ", "ै"), ("au", "औ", "ौ"), ("ie", "इए", "िए"),
        ("a", "अ", ""),   ("e", "ए", "े"),  ("i", "इ", "ि"),
        ("o", "ओ", "ो"),  ("u", "उ", "ु")
    ]

    tokens = []
    i = 0
    n = len(w)

    while i < n:
        matched = False

        # Match nasal ending 'n'
        if w[i] == 'n' and (i == n - 1 or (i < n - 1 and w[i+1] not in "aeiou")):
            tokens.append(('NASAL', 'ं'))
            i += 1
            continue

        # Match consonants
        for roman, dev in CONSONANT_MAP:
            if w.startswith(roman, i):
                tokens.append(('CONSONANT', dev))
                i += len(roman)
                matched = True
                break
        if matched:
            continue

        # Match vowels
        for roman, indep, matra in VOWEL_MAP:
            if w.startswith(roman, i):
                tokens.append(('VOWEL', (indep, matra)))
                i += len(roman)
                matched = True
                break
        if matched:
            continue

        tokens.append(('OTHER', w[i]))
        i += 1

    # Assemble Devanagari string from parsed tokens
    res = []
    prev_type = None

    for token_type, val in tokens:
        if token_type == 'CONSONANT':
            res.append(val)
            prev_type = 'CONSONANT'
        elif token_type == 'VOWEL':
            indep, matra = val
            if prev_type == 'CONSONANT':
                res.append(matra)  # Attach Matra to consonant
            else:
                res.append(indep)  # Independent vowel at word start or after vowel
            prev_type = 'VOWEL'
        elif token_type == 'NASAL':
            res.append(val)
            prev_type = 'NASAL'
        else:
            res.append(val)
            prev_type = token_type

    return "".join(res)


def transliterate_urdu_script_to_devanagari(text: str) -> str:
    tokens = re.split(r"(\s+|[.,!?۔؟—\-\"'():;«»])", text)
    result = []
    for token in tokens:
        clean_token = token.strip()
        if clean_token in URDU_SCRIPT_WORD_MAP:
            result.append(URDU_SCRIPT_WORD_MAP[clean_token])
        elif clean_token:
            word = clean_token
            for digraph, dev_char in URDU_DIGRAPHS.items():
                word = word.replace(digraph, dev_char)
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
    tokens = re.split(r"(\s+|[.,!?۔؟—\-\"'():;«»])", text)
    result = []
    for token in tokens:
        lower_token = token.lower().strip()
        if lower_token in ROMAN_TO_DEVANAGARI_WORDS:
            result.append(ROMAN_TO_DEVANAGARI_WORDS[lower_token])
        elif lower_token and lower_token.isalpha():
            result.append(fallback_roman_to_devanagari(lower_token))
        else:
            result.append(token)
    return "".join(result)


def prepare_text_for_tts(text: str) -> tuple[str, str]:
    if not text or not text.strip():
        return "", "en"

    has_urdu_script = bool(re.search(r"[\u0600-\u06FF]", text))
    if has_urdu_script:
        return transliterate_urdu_script_to_devanagari(text.strip()), "hi"

    cleaned_text = fix_roman_urdu_misspellings(text)
    return transliterate_roman_to_devanagari(cleaned_text).strip(), "hi"
