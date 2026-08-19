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
    "ج": "ज", "چ": "च", "ح": "ह",
    "خ": "ख़",  # BUG FIX: was plain "ख" (aspirated k-sound). خ is the
               # guttural fricative /x/ (like German "ch" in "Bach"),
               # which Devanagari marks with a nuqta — ख़, not ख. Every
               # word using خ (خاص, خوش, خواب, خدمت...) was silently
               # losing this distinction at the TEXT level, not just at
               # the audio level.
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

# ---- Word-level pronunciation overrides ----
# Standard written Urdu omits short-vowel diacritics (see HONEST LIMITATION
# above), so the character-by-character mapper has no way to know whether
# an unmarked consonant carries an 'a', 'i', or 'u' sound — it defaults to
# 'a', which is wrong for a large share of everyday vocabulary (Persian/
# Arabic loanwords especially, since their vowel patterns don't follow
# native Hindustani rules the char-level mapper assumes). Rather than
# trying to teach the character-level algorithm Urdu's un-written
# vowel-harmony/loanword rules — a losing battle, since these words are
# irregular by nature, which is WHY Urdu writing doesn't bother marking
# them — this table hardcodes the correct, standard Hindi spelling
# directly for common words where the character-level default is wrong.
# Checked BEFORE falling through to character-by-character conversion, so
# any word in this table renders correctly regardless of what the general
# rules would otherwise produce.
#
# Every entry below was verified against transliterate_urdu_to_devanagari()
# ACTUAL prior output (not guessed) to confirm it was genuinely wrong
# before being added — several plausible-looking candidates (یقین, اہم,
# مقصد, طاقت, قریب, عمل, لوگوں, سمجھ) already came out correct and were
# deliberately left OUT of this table, to keep it from accumulating
# redundant entries that do nothing.
#
# MAINTENANCE: if a specific word keeps mispronouncing in real use, add it
# here — same verify-before-adding process: run
# transliterate_urdu_to_devanagari("word") first, confirm it's actually
# wrong, only then add the correct spelling below.
_WORD_OVERRIDES = {
    "دل": "दिल",
    "علم": "इल्म",
    "علموں": "इल्मों",
    "ہمت": "हिम्मत",
    "مشکل": "मुश्किल",
    "مشکلات": "मुश्किलात",
    "خدمت": "ख़िदमत",
    "استاد": "उस्ताद",
    "سکون": "सुकून",
    "مستقبل": "मुस्तक़बिल",
    "مستقل": "मुस्तक़िल",
    "زندگی": "ज़िंदगी",
    "وقت": "वक़्त",
    "دوست": "दोस्त",
    "دوستی": "दोस्ती",
    "خواب": "ख़्वाब",
    "خوابوں": "ख़्वाबों",
    "فیصلے": "फ़ैसले",
    "فیصلہ": "फ़ैसला",
    "محبت": "मोहब्बत",
    "خیال": "ख़याल",
    "امید": "उम्मीद",
    "معلوم": "मालूम",
    "سچائی": "सच्चाई",
    "انسان": "इंसान",
    "انسانوں": "इंसानों",
    "دنیا": "दुनिया",
    "خاصیت": "ख़ासियत",
    "تعلیم": "तालीम",
    "نعمت": "नेमत",
    "عادت": "आदत",
    "خوش": "ख़ुश",
    "خوشی": "ख़ुशी",
    "خوشیاں": "ख़ुशियां",
    "محنت": "मेहनत",
    "مزاجی": "मिज़ाजी",
    "طالب": "तालिब",
    "کتاب": "किताब",
    "کتابوں": "किताबों",
    "چاہیے": "चाहिए",
    "زیادہ": "ज़्यादा",
    "تحفہ": "तोहफ़ा",
    "خاص": "ख़ास",
    "بدلہ": "बदला",
    "نیکی": "नेकी",
    "نیکیاں": "नेकियां",
    # Ultra-high-frequency function/grammar words — these appear in nearly
    # every sentence, so getting them right matters more than almost any
    # content word. Same verified-mismatch process as above.
    "ہے": "है",
    "ہیں": "हैं",
    "میں": "में",
    "کیا": "क्या",
    "کیوں": "क्यों",
    "کون": "कौन",
    "بہت": "बहुत",
    "اچھا": "अच्छा",
    "اچھی": "अच्छी",
    "اچھے": "अच्छे",
    "کچھ": "कुछ",
    "درست": "दुरुस्त",
    "ایک": "एक",
    # Round 2 — found via a real listening test against this dictionary's
    # first version. Same verify-before-adding process as always.
    "خلوص": "ख़ुलूस",
    "مثبت": "मुसबत",
    "معنی": "मानी",
    "دلوں": "दिलों",
}


def contains_urdu_script(text: str) -> bool:
    """True if the text contains Perso-Arabic script characters — used to
    decide whether transliteration is needed at all, so English or
    already-Devanagari (Hindi) text passes through untouched."""
    return bool(_URDU_SCRIPT_RE.search(text or ""))


def _transliterate_word_chars(word: str) -> str:
    """Character-by-character conversion for a single word (may include
    trailing punctuation) — the original algorithm, unchanged, just scoped
    to one word instead of the whole string. Scoping to a word doesn't
    change behavior: prev_was_consonant already reset at every whitespace
    boundary anyway, since no medial-vowel or shadda rule looks across a
    space."""
    result = []
    i = 0
    n = len(word)
    prev_was_consonant = False

    while i < n:
        ch = word[i]

        # Aspirated digraphs (2-char lookahead) take priority.
        if i + 1 < n:
            pair = word[i:i + 2]
            if pair in _ASPIRATED_DIGRAPHS:
                result.append(_ASPIRATED_DIGRAPHS[pair])
                prev_was_consonant = True
                i += 2
                continue

        # Multi-character independent vowel sequences at a word boundary.
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


def transliterate_urdu_to_devanagari(text: str) -> str:
    """Best-effort Urdu -> Hindi (Devanagari) transliteration. See module
    docstring for the honest accuracy caveat. Non-Urdu characters (spaces,
    Latin text, punctuation, digits) pass through unchanged.

    Checks each word against _WORD_OVERRIDES first (see that table's
    docstring for why) — only words NOT in the table fall through to the
    character-by-character rules below.
    """
    if not text:
        return text

    # Split on whitespace but KEEP the whitespace itself (capturing group),
    # so the exact spacing of the input is reproduced exactly on output —
    # this also naturally isolates each word for the override lookup.
    segments = re.split(r"(\s+)", text)
    out = []
    for seg in segments:
        if not seg or seg.isspace():
            out.append(seg)
            continue

        # Strip trailing punctuation before checking the override table —
        # a sentence-final "دل۔" needs to match the dictionary's "دل" —
        # then re-attach the (transliterated) punctuation afterward.
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

    return "".join(out)


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
