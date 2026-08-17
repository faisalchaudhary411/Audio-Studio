"""
urdu_transliteration.py — Urdu (Perso-Arabic script) -> Hindi (Devanagari
script) transliteration.

WHY THIS EXISTS: Chatterbox Multilingual (the voice-clone model) supports
Hindi but not Urdu directly. Urdu and Hindi are the same spoken language
(Hindustani) — they differ only in script, not in phonology. So Urdu text
transliterated into Devanagari and fed to the model's Hindi mode should be
pronounced correctly, since the model is reproducing the actual sounds, not
the spelling.

ORIGINAL IMPLEMENTATION — not derived from any third-party library. Two
existing options were evaluated and rejected specifically because neither
has a LICENSE file in its repo (default copyright applies, not safe to
depend on for a paid feature without asking the author):
  - GokulNC/Indic-PersoArabic-Script-Converter (PyPI: indo-arabic-
    transliteration) — no LICENSE file, marked "WIP", and its own README
    says the rule-based method "will not be accurate, especially for
    Arabic-to-Indic" (our exact direction).
  - asghar-rizvi's Urdu SpeechT5 project — no LICENSE file, and its own
    README describes the model itself as "mid-level quality."
This mapping is instead built directly from the well-documented, public
Perso-Arabic/Devanagari phonetic correspondence (see e.g. Wikipedia's
"Hindustani orthography" and "Hindi-Urdu transliteration" articles for the
underlying linguistic facts — a character correspondence table, not
copyrightable expression).

HONEST LIMITATION: standard written Urdu omits short-vowel diacritics
(zabar/zer/pesh), the same way standard written Arabic does — a reader
infers them from context and vocabulary knowledge. This mapper can only
transliterate what's actually written, so short vowels default to the
Devanagari inherent 'a' sound where no diacritic is present, same as any
rule-based approach (including the "official" government tools referenced
by both rejected libraries, which carry the identical limitation). This
will be noticeably better than sending raw Urdu script into a Hindi-only
model (which would likely ignore/mispronounce unrecognized characters
entirely), but it is a best-effort phonetic approximation, not
publication-grade Hindi spelling — test with real users and adjust the
mapping tables below if particular words consistently mispronounce.
"""

import re

# ---- Consonants (final Devanagari includes inherent 'a', matching how
#      Devanagari consonants normally work) ----
_CONSONANTS = {
    "ب": "ब", "پ": "प", "ت": "त", "ٹ": "ट", "ث": "स",
    "ج": "ज", "چ": "च", "ح": "ह", "خ": "ख",
    "د": "द", "ڈ": "ड", "ذ": "ज़",
    "ر": "र", "ڑ": "ड़", "ز": "ज़", "ژ": "ज़",
    "س": "स", "ش": "श", "ص": "स", "ض": "ज़",
    "ط": "त", "ظ": "ज़", "غ": "ग़", "ف": "फ़", "ق": "क़",
    "ک": "क", "گ": "ग", "ل": "ल", "م": "म", "ن": "न",
    "ں": "ं",  # noon ghunna -> anusvara (nasalization)
    "ہ": "ह", "ھ": "ह",
    "و": "व",  # vau's DEFAULT role is consonant 'v' — overridden to a vowel
               # matra by _MEDIAL_VOWELS below when it directly follows a
               # consonant with no vowel of its own yet, which is the far
               # more common role in running Urdu text (long o/u sounds).
    "ی": "य",  # choti ye's DEFAULT role is consonant 'y' — same override
               # logic as و above for its long-i vowel role.
    "ء": "",  # hamza (glottal stop) — no clean Devanagari equivalent, drop
    "ئ": "य",  # hamza-on-yeh — same fallback as ی, best available approximation
    "ع": "",  # ain mid-word — genuinely ambiguous/near-silent, drop (word-
              # initial ain is handled separately below as a vowel carrier)
}

# Aspirated digraphs — Urdu marks aspiration with a following do-chashmi
# heh (ھ), Devanagari marks it with a dedicated letter. Must be matched
# BEFORE the single-consonant table above, longest-match-first.
_ASPIRATED_DIGRAPHS = {
    "بھ": "भ", "پھ": "फ", "تھ": "थ", "ٹھ": "ठ", "دھ": "ध", "ڈھ": "ढ",
    "کھ": "ख", "گھ": "घ", "چھ": "छ", "جھ": "झ",
}

# ---- Vowels ----
# Independent alif (ا) at word start is a vowel carrier; medial/final و and
# ی behave as long vowels far more often than as consonants in practice, so
# default them to vowel forms — this is the single biggest simplification
# here and the most common source of mismatches worth manually reviewing.
_INDEPENDENT_VOWEL_START = {
    "ا": "अ", "آ": "आ", "او": "औ", "اے": "ऐ", "ای": "ई", "اُو": "ऊ",
    "ع": "अ",  # word-initial ain commonly functions as a vowel carrier,
               # same simplification as alif — mid-word occurrences are
               # handled separately in _CONSONANTS (dropped, see above)
}
_MEDIAL_VOWELS = {
    "ا": "ा",  # alif after a consonant = long aa
    "و": "ो",  # vau as vowel = o (also commonly u/oo — see limitation note above)
    "ی": "ी",  # choti ye as vowel = long ee
    "ے": "े",  # badi ye = e/ai
}

# ---- Diacritics (rarely present in everyday written Urdu, but honored if given) ----
_DIACRITICS = {
    "\u064e": "",       # zabar (fatha) — inherent 'a' already default in Devanagari, no mark needed
    "\u0650": "\u093f",  # zer (kasra) -> Devanagari i-matra
    "\u064f": "\u0941",  # pesh (damma) -> Devanagari u-matra
    "\u0651": None,      # shadda (gemination) — handled specially: doubles preceding consonant
    "\u0652": "\u094d",  # sukun (no vowel) -> Devanagari virama (suppresses inherent 'a')
}

# ---- Punctuation — Urdu uses Perso-Arabic punctuation marks that a TTS
#      model (expecting standard/Devanagari punctuation for prosody cues
#      like question intonation and pause length) likely won't recognize
#      as such if left as raw Arabic-script symbols. ----
_PUNCTUATION = {
    "؟": "?", "،": ",", "۔": ".",
}

_URDU_SCRIPT_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def contains_urdu_script(text: str) -> bool:
    """True if the text contains Perso-Arabic script characters — used to
    decide whether transliteration is needed at all, so English or
    already-Devanagari (Hindi) text passes through untouched."""
    return bool(_URDU_SCRIPT_RE.search(text or ""))


def transliterate_urdu_to_devanagari(text: str) -> str:
    """Best-effort Urdu -> Hindi (Devanagari) transliteration. See module
    docstring for the honest accuracy caveat. Non-Urdu characters (spaces,
    Latin text, punctuation, digits) pass through unchanged."""
    if not text:
        return text

    result = []
    i = 0
    n = len(text)
    prev_was_consonant = False

    while i < n:
        ch = text[i]

        # Aspirated digraphs (2-char lookahead) take priority.
        if i + 1 < n:
            pair = text[i:i + 2]
            if pair in _ASPIRATED_DIGRAPHS:
                result.append(_ASPIRATED_DIGRAPHS[pair])
                prev_was_consonant = True
                i += 2
                continue

        # Multi-character independent vowel sequences at a word boundary.
        if not prev_was_consonant:
            matched = False
            for seq in sorted(_INDEPENDENT_VOWEL_START, key=len, reverse=True):
                if text[i:i + len(seq)] == seq:
                    result.append(_INDEPENDENT_VOWEL_START[seq])
                    prev_was_consonant = False
                    i += len(seq)
                    matched = True
                    break
            if matched:
                continue

        # Shadda: double the previous consonant's sound (approximate by
        # repeating the last emitted Devanagari consonant character).
        if ch == "\u0651" and result:
            result.append(result[-1])
            i += 1
            continue

        # Other diacritics.
        if ch in _DIACRITICS:
            mapped = _DIACRITICS[ch]
            if mapped:
                result.append(mapped)
            i += 1
            continue

        # Medial/final vowel forms (only meaningful right after a consonant).
        if prev_was_consonant and ch in _MEDIAL_VOWELS:
            result.append(_MEDIAL_VOWELS[ch])
            prev_was_consonant = False
            i += 1
            continue

        # Punctuation.
        if ch in _PUNCTUATION:
            result.append(_PUNCTUATION[ch])
            prev_was_consonant = False
            i += 1
            continue

        # Plain consonants.
        if ch in _CONSONANTS:
            result.append(_CONSONANTS[ch])
            prev_was_consonant = True
            i += 1
            continue

        # Anything else (spaces, Latin letters, digits, punctuation,
        # unrecognized marks) passes through unchanged.
        result.append(ch)
        prev_was_consonant = False
        i += 1

    return "".join(result)


def prepare_text_for_tts(text: str) -> tuple:
    """Single entry point clone_engine.py calls before submitting to the
    Modal worker. Returns (processed_text, language_id):
      - Urdu script detected -> transliterated to Devanagari, language_id="hi"
        (Chatterbox Multilingual has no Urdu mode; Urdu and Hindi are the
        same spoken language, so this is a legitimate substitution, not a
        hack — see module docstring)
      - Devanagari (Hindi) already -> passed through unchanged, language_id="hi"
      - Anything else -> passed through unchanged, language_id="en"
    Mixed-script input transliterates only the Urdu portions; a sentence
    that's mostly English with a few Urdu words will still get "hi" as the
    language_id, which is the right call more often than not for that case
    but isn't perfect — genuinely mixed-language sentences are an inherent
    hard case for any single-language_id TTS call, not something either
    script-detection or transliteration can fully solve on their own.
    """
    if contains_urdu_script(text):
        return transliterate_urdu_to_devanagari(text), "hi"
    if _DEVANAGARI_RE.search(text or ""):
        return text, "hi"
    return text, "en"
