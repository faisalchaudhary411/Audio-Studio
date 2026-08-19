"""
urdu_transliteration.py — Improved Urdu (Perso-Arabic script) -> Hindi (Devanagari
script) transliteration engine for Chatterbox TTS.
"""

import re

# ---- Consonants ----
_CONSONANTS = {
    "ب": "ब", "پ": "प", "ت": "त", "ٹ": "ट", "ث": "स",
    "ج": "ज", "چ": "च", "ح": "ह",
    "خ": "ख़",
    "د": "द", "ڈ": "ड", "ذ": "ज़",
    "ر": "र", "ڑ": "ड़", "ز": "ज़", "ژ": "ज़",
    "س": "स", "ش": "श", "ص": "स", "ض": "ज़",
    "ط": "त", "ظ": "ज़", "غ": "ग़", "ف": "फ़", "ق": "क़",
    "ک": "क", "گ": "ग", "ل": "ल", "م": "म", "ن": "न",
    "ہ": "ह", "ھ": "ह",
    "و": "व",
    "ی": "य",
    "ء": "",
    "ئ": "य",
}

# Aspirated digraphs — matched before single consonants
_ASPIRATED_DIGRAPHS = {
    "بھ": "भ", "پھ": "फ", "تھ": "थ", "ٹھ": "ठ", "دھ": "ध", "ڈھ": "ढ",
    "کھ": "ख", "گھ": "घ", "چھ": "छ", "جھ": "झ",
}

# ---- Vowels ----
_INDEPENDENT_VOWEL_START = {
    "ا": "अ", "آ": "आ", "او": "औ", "اے": "ऐ", "ای": "ई", "اُو": "ऊ",
    "ع": "अ",
}

_MEDIAL_VOWELS = {
    "ا": "ा",
    "و": "ो",  # Default medial vau -> o (long 'oo' and 'au' handled via _WORD_OVERRIDES)
    "ی": "ी",
    "ے": "े",
}

# ---- Diacritics ----
_DIACRITICS = {
    "\u064e": "",        # Zabar
    "\u0650": "\u093f",  # Zer -> i-matra
    "\u064f": "\u0941",  # Pesh -> u-matra
    "\u0651": None,      # Shadda (handled in loop)
    "\u0652": "\u094d",  # Sukun -> virama
}

# ---- Punctuation ----
_PUNCTUATION = {
    "؟": "?", "،": ",", "۔": ".",
}

_URDU_SCRIPT_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# ---- High-Frequency Word Overrides ----
_WORD_OVERRIDES = {
    # Core vocabulary
    "دل": "दिल", "علم": "इल्म", "علموں": "इल्मों", "ہمت": "हिम्मत",
    "مشکل": "मुश्किल", "مشکلات": "मुश्किलात", "خدمت": "ख़िदमत",
    "استاد": "उस्ताद", "سکون": "सुकून", "مستقبل": "मुस्तक़बिल",
    "مستقل": "मुस्तक़िल", "زندگی": "ज़िंदगी", "وقت": "वक़्त",
    "دوست": "दोस्त", "دوستی": "दोस्ती", "خواب": "ख़्वाब",
    "خوابوں": "ख़्वाबों", "فیصلے": "फ़ैसले", "فیصلہ": "फ़ैसला",
    "محبت": "मोहब्बत", "خیال": "ख़याल", "امید": "उम्मीद",
    "معلوم": "मालूम", "سچائی": "सच्चाई", "انسان": "इंसान",
    "انسانوں": "इंसानों", "دنیا": "दुनिया", "خاصیت": "ख़ासियत",
    "تعلیم": "तालीम", "نعمت": "नेमत", "عادت": "आदत",
    "خوش": "ख़ुश", "خوشی": "ख़ुशी", "خوشیاں": "ख़ुशियां",
    "محنت": "मेहनत", "مزاجی": "मिज़ाजी", "طالب": "तालिब",
    "کتاب": "किताब", "کتابوں": "किताबों", "چاہیے": "चाहिए",
    "زیادہ": "ज़्यादा", "تحفہ": "तोहफ़ा", "خاص": "ख़ास",
    "بدلہ": "बदला", "نیکی": "नेकी", "نیکیاں": "नेकियां",
    "خلوص": "ख़ुलूस", "مثبت": "मुसबत", "معنی": "मानी", "دلوں": "दिलों",
    "ہے": "है", "ہیں": "हैं", "میں": "में", "کیا": "क्या",
    "کیوں": "क्यों", "کون": "कौन", "بہت": "बहुत", "اچھا": "अच्छा",
    "اچھی": "अच्छी", "اچھے": "अच्छे", "کچھ": "कुछ", "درست": "दुरुस्त",
    "ایک": "एक",

    # Words with Long 'oo' (ू)
    "نور": "नूर", "ضرور": "ज़रूर", "ضرورت": "ज़रूरत", "حضور": "हज़ूर",
    "مجبور": "मजबूर", "مقبول": "मक़बूल", "مشہور": "मशहूर", "شروع": "शुरू",
    "دور": "दूर", "صورت": "सूरत", "خوبصورت": "ख़ूबसूरत", "حکومت": "हुकूमत",
    "قانون": "क़ानून", "دستور": "दस्तूर",

    # Words with 'au' (ौ)
    "قوم": "क़ौम", "فوج": "फ़ौज", "موقع": "मौक़ा", "شوق": "शौक़",
    "ذوق": "ज़ौक़", "موت": "मौत", "عورت": "औरत",

    # Words with mid-word Ain (ع)
    "بعد": "बाद", "شاعر": "शायर", "شعر": "शेर", "شاعری": "शायरी",
    "تعریف": "तारीफ़", "یعنی": "यानी", "عزت": "इज़्ज़त", "عقل": "अक़्ल",
    "علاقہ": "इलाक़ा", "علاقے": "इलाक़े", "عوامی": "अवामी", "جمع": "जमा",
    "واقعہ": "वाक़िया", "دعویٰ": "दावा",

    # Loanwords & short-vowel patterns
    "طرح": "तरह", "طرف": "तरफ़", "کرم": "करम", "نرم": "नरम",
    "شرم": "शर्म", "شکل": "शक्ल", "نظر": "नज़र", "خبر": "ख़बर",
    "سفر": "सफ़र", "سبق": "सबक़", "فرض": "फ़र्ज़", "قرض": "क़र्ज़",
    "عرض": "अर्ज़", "مرض": "मर्ज़", "حکم": "हुक्م", "ظلم": "ज़ुल्म",
    "کمرہ": "कमरा", "وجہ": "वजह", "جگہ": "जगह",
}


def contains_urdu_script(text: str) -> bool:
    """Check if string contains Perso-Arabic characters."""
    return bool(_URDU_SCRIPT_RE.search(text or ""))


def _transliterate_word_chars(word: str) -> str:
    """Character-level transliteration logic with dynamic context rules."""
    result = []
    i = 0
    n = len(word)
    prev_was_consonant = False

    while i < n:
        ch = word[i]

        # 1. Aspirated digraphs (2-char lookahead)
        if i + 1 < n:
            pair = word[i:i + 2]
            if pair in _ASPIRATED_DIGRAPHS:
                result.append(_ASPIRATED_DIGRAPHS[pair])
                prev_was_consonant = True
                i += 2
                continue

        # 2. Multi-character independent initial vowels
        if not prev_was_consonant:
            matched = False
            for seq in sorted(_INDEPENDENT_VOWEL_START, key=len, reverse=True):
                if word[i:i + len(seq)] == seq:
                    result.append(_INDEPENDENT_VOWEL_START[seq])
                    prev_was_consonant = False
                    i += len(seq)
                    matched = True
                    break
            if matched:
                continue

        # 3. Shadda (gemination)
        if ch == "\u0651" and result:
            result.append(result[-1])
            i += 1
            continue

        # 4. Smart Noon Ghunna (ں) nasalization rule
        if ch == "ں":
            upper_matras = {"े", "ै", "ी", "ो", "ौ", "ं"}
            if result and result[-1] in upper_matras:
                result.append("ं")
            else:
                result.append("ँ")
            prev_was_consonant = False
            i += 1
            continue

        # 5. Smart Ain (ع) mid-word handling
        if ch == "ع":
            if prev_was_consonant:
                if i + 1 < n and word[i + 1] in _CONSONANTS:
                    result.append("ा")
                else:
                    result.append("अ")
            else:
                result.append("अ")
            prev_was_consonant = False
            i += 1
            continue

        # 6. Diacritics
        if ch in _DIACRITICS:
            mapped = _DIACRITICS[ch]
            if mapped:
                result.append(mapped)
            i += 1
            continue

        # 7. Medial/final vowels
        if prev_was_consonant and ch in _MEDIAL_VOWELS:
            result.append(_MEDIAL_VOWELS[ch])
            prev_was_consonant = False
            i += 1
            continue

        # 8. Punctuation
        if ch in _PUNCTUATION:
            result.append(_PUNCTUATION[ch])
            prev_was_consonant = False
            i += 1
            continue

        # 9. Plain consonants
        if ch in _CONSONANTS:
            result.append(_CONSONANTS[ch])
            prev_was_consonant = True
            i += 1
            continue

        # Passthrough unmapped characters
        result.append(ch)
        prev_was_consonant = False
        i += 1

    return "".join(result)


def transliterate_urdu_to_devanagari(text: str) -> str:
    """Transliterates Urdu text into Devanagari script."""
    if not text:
        return text

    segments = re.split(r"(\s+)", text)
    out = []
    for seg in segments:
        if not seg or seg.isspace():
            out.append(seg)
            continue

        core = seg
        trailing = ""
        while core and core[-1] in _PUNCTUATION:
            trailing = core[-1] + trailing
            core = core[:-1]

        if core in _WORD_OVERRIDES:
            out.append(_WORD_OVERRIDES[core])
            out.append(_transliterate_word_chars(trailing))
        else:
            out.append(_transliterate_word_chars(seg))

    # Normalize punctuation spacing for natural TTS prosody
    formatted_text = "".join(out)
    formatted_text = re.sub(r'([.,?])(?=[^\s])', r'\1 ', formatted_text)
    return formatted_text


def prepare_text_for_tts(text: str) -> tuple:
    """Prepares input text and returns (processed_text, language_id)."""
    if contains_urdu_script(text):
        return transliterate_urdu_to_devanagari(text), "hi"
    if _DEVANAGARI_RE.search(text or ""):
        return text, "hi"
    return text, "en"
