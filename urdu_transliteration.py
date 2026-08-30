"""
urdu_transliteration.py — Universal Transliteration for Roman Urdu & Native Urdu Script.
Converts any Urdu input (Dictionary matched or OOV) into clean Devanagari for Chatterbox TTS.
"""

import re

# ── 1. Native Urdu Script (Perso-Arabic) Word Map ──────────────────────────────
# High-coverage dictionary of common words (preferred over character rules)
URDU_SCRIPT_WORD_MAP = {
    # Added from OOV report — bypasses fallback for words it consistently mishandles.
    "اٹھانے": "उठाने",
    "غیر": "ग़ैर",
    # NOTE: report proposed "ज़िहनी" (Zihni) but ذہنی derives from ذہن
    # (zehn, "mind") — correct pronunciation is "zehni", matching ज़हनी
    # already verified earlier against native pronunciation, not ज़िहनी.
    "ذہنی": "ज़हनी",
    "عادتیں": "आदतें",
    "جسمانی": "जिस्मानी",
    "کرواتے": "करवाते",
    "بہتری": "बेहतरी",
    "استعمال": "इस्तेमाल",
    "نظم": "नज़्म",
    "ضبط": "ज़ब्त",
    # Phrase-level entries (require the phrase-matching lookup below —
    # single-token-only lookup would map "انہوں" alone to "उन्होंने" and
    # then ALSO translate the separate trailing "نے" token, duplicating
    # "ने" -> "उन्होंने ने". Keeping these as two-word keys avoids that.
    "انہوں نے": "उन्होंने",
    "جنہوں نے": "जिन्होंने",
    "نظم و ضبط": "नज़्म-ओ-ज़ब्त",
    # Function Words & Possessives
    "کی": "की", "کا": "का", "کے": "के", "کو": "को", "میں": "में", "سے": "से",
    "پر": "पर", "بھی": "भी", "کل": "कल", "یہ": "यह", "وہ": "वह", "تھا": "था",
    "تھی": "थी", "تھے": "थे", "ہے": "है", "ہیں": "हैं", "ہو": "हो", "ہونا": "होना",
    "چاہیے": "चाहिए", "نہ": "ना", "لیکن": "लेकिन", "جس": "जिस", "موڑ": "मोड़",
    "سبق": "सबक़", "راستے": "रास्ते", "مشکلات": "मुश्किलात", "سامنے": "सामने",
    "اور": "और", "تو": "तो", "اگر": "अगर", "پھر": "फिर", "اب": "अब", "تب": "तब",
    "کب": "कब", "کہاں": "कहाँ", "کیوں": "क्यों", "کیسے": "कैसे", "کون": "कौन",
    "کیا": "क्या", "ہاں": "हाँ", "نہیں": "नहीं", "صرف": "सिर्फ़", "بہت": "बहुत",
    "کچھ": "कुछ", "سب": "सब", "ہر": "हर", "کوئی": "कोई", "سبھی": "सभी",

    # Vocabulary
    "زندگی": "ज़िंदगी", "ایک": "एक", "خاص": "खास", "تحفہ": "तोहफा", "ہم": "हम",
    "خوش": "खुश", "چھوٹی": "छोटी", "خوشیاں": "खुशियां", "معنی": "मानी",
    "دیتی": "देती", "صبح": "सुबह", "جلدی": "जल्दी", "اٹھنا": "उठना", "اچھی": "अच्छी",
    "اچھا": "अच्छा", "اچھے": "अच्छे", "عادت": "आदत", "اس": "इस", "دن": "दिन",
    "بنتا": "बनता", "کتابوں": "किताबों", "سیکھنا": "सीखना", "سیکھنے": "सीखने",
    "علم": "इल्म", "انسان": "इंसान", "طاقت": "ताकत", "دیتا": "देता", "ہمیشہ": "हमेशा",
    "نیا": "नया", "نئی": "नयी", "ذہن": "ज़हन", "کھلتا": "खुलता",
    "کھلا": "खुला", "باتیں": "बातें", "سمجھتا": "समझता", "سمجھ": "समझ",
    "آسان": "आसान", "بنتی": "बनती", "پسند": "पसंद", "دوستی": "दोस्ती",
    "بناتی": "बनाती", "دوست": "दोस्त", "ساتھ": "साथ", "دیتے": "देते",
    "مشکل": "मुश्किल", "وقت": "वक्त", "ہی": "ही", "کام": "काम", "آتے": "आते",
    "محبت": "मोहब्बत", "خلوص": "ख़ुलूस", "دلوں": "दिलों", "ملاتی": "मिलाती",
    "لوگوں": "लोगों", "مدد": "मदद", "دینا": "देना", "عمل": "अमल", "دل": "दिल",
    "ہوتا": "होता", "آتا": "आता", "امید": "उम्मीद", "آگے": "आगे", "لے": "ले",
    "جاتی": "जाती", "خواب": "ख्वाब", "دیکھنا": "देखना", "بات": "बात",
    "خوابوں": "ख्वाबों", "سچ": "सच", "بنانے": "बनाने", "محنت": "मेहनत",
    "کبھی": "कभी", "ضائع": "ज़ाया", "انسانوں": "इंसानों",
    "خاصیت": "खासियत", "ہوتی": "होती", "اپنے": "अपने",
    "آپ": "आप", "یقین": "यकीन", "اہم": "अहम", "ہمت": "हिम्मत", "ملتی": "मिलती",
    "ملتا": "मिलता", "کامیابی": "कामयाबी", "مستقل": "मुस्तक़िल", "مزاجی": "मिज़ाजी",
    "سوچ": "सोच", "مثبت": "मुस्बत", "فائدہ": "फ़ायदा", "دونوں": "दोनों",
    "حالتوں": "हालतों", "سکون": "सुकून", "فیصلے": "फैसले", "ہوتے": "होते",
    "مستقبل": "मुस्तक़बिल", "آج": "आज", "پھل": "फल", "سچائی": "सच्चाई",
    "معلوم": "मालूम", "ہونی": "होनी", "ساتھی": "साथी",
    "تعلیم": "तालीम", "نعمت": "नेमत", "استاد": "उस्ताद", "طالب": "तालिब",
    "علموں": "इल्मों", "بدل": "बदल", "تنہا": "तन्हा", "نیکی": "नेकी",
    "بدلہ": "बदला", "خدمت": "ख़िदमत", "لوگ": "लोग", "بناتے": "बनाते",
    "اچھائی": "अच्छाई", "ملتے": "मिलते", "نیکیاں": "नेकियां", "خوشی": "खुशी",
    "بڑھاتا": "बढ़ाता", "والا": "वाला", "سفر": "सफ़र", "ایسا": "ऐसा", "ایسی": "ऐसी",
    "ایسے": "ऐसे", "وہاں": "वहाँ", "یہاں": "यहाँ", "کے لیے": "के लिए",
    "کے لئے": "के लिए", "لیے": "लिए", "لئے": "लिए", "کرنا": "करना", "کرنے": "करने",
    "کرتا": "करता", "کرتی": "करती", "کرتے": "करते", "کیا": "किया", "کیے": "किए",
    "گیا": "गया", "گئی": "गई", "گئے": "गए", "ہوا": "हुआ", "ہوئی": "हुई", "ہوئے": "हुए",
    "رہا": "रहा", "رہی": "रही", "رہے": "रहे", "جا": "जा", "آ": "आ", "دے": "दे",
    "لے لو": "ले लो", "دیکھو": "देखो", "سنو": "सुनो", "پڑھو": "पढ़ो",
    "لکھو": "लिखो", "بولو": "बोलो", "چلو": "चलो", "رکھو": "रखो",
    "خوبصورت": "खूबसूरत", "ضروری": "ज़रूरी", "ضرور": "ज़रूर", "رات": "रात",
    "دن": "दिन", "صبح": "सुबह", "شام": "शाम", "دنیا": "दुनिया", "آسمان": "आसमान",
    "زمین": "ज़मीन", "پانی": "पानी", "آگ": "आग", "ہوا": "हवा", "روشنی": "रोशनी",
    "اندھیرا": "अंधेरा", "اندھیری": "अंधेरी", "خوشی": "खुशी", "غم": "ग़म",
    "محبت": "मोहब्बत", "نفرت": "नफ़रत", "دوستی": "दोस्ती", "دشمنی": "दुश्मनी",
    "کامیابی": "कामयाबी", "ناکامی": "नाकामी", "محنت": "मेहनत", "کوشش": "कोशिश",
    "ہمت": "हिम्मत", "حوصلہ": "हौसला", "صبر": "सब्र", "شکر": "शुक्र",
    "دعا": "दुआ", "الله": "अल्लाह", "خدا": "ख़ुदा", "رب": "रब",
    "پیار": "प्यार", "محبتیں": "मोहब्बतें", "ارمان": "अरमान", "خواب": "ख्वाब",
    "حقیقت": "हक़ीक़त", "سچ": "सच", "جھوٹ": "झूठ", "حق": "हक़", "باطل": "बातिल",
    "انصاف": "इंसाफ़", "ظلم": "ज़ुल्म", "عدل": "अदल", "امان": "अमान",
    "امن": "अमन", "جنگ": "जंग", "صلح": "सुल्ह", "فتح": "फ़तह", "شکست": "शिकस्त",
    "فتحیاب": "फ़तहयाब", "کامیاب": "कामयाब", "ناکام": "नाकाम",
    "مضبوط": "मज़बूत", "کمزور": "कमज़ोर", "طاقتور": "ताक़तवर", "بے بس": "बेबस",
    "آزاد": "आज़ाद", "غلام": "ग़ुलाम", "آزادی": "आज़ादी", "غلامی": "ग़ुलामी",
    "ترقی": "तरक़्क़ी", "پسماندگی": "पसमंदगी", "ترقی یافتہ": "तरक़्क़ीयाफ़्ता",
    "علمی": "इल्मी", "عملی": "अमली", "نظری": "नज़री", "تجربہ": "तज्रिबा",
    "تجربے": "तज्रिबे", "سبق": "सबक़", "سبق آموز": "सबक़आमोज़",
    "استاد": "उस्ताद", "شاگرد": "शागिर्द", "طالب علم": "तालिब इल्म",
    "کتاب": "किताब", "قلم": "क़लम", "کاغذ": "काग़ज़", "صفحہ": "सफ़हा",
    "صفحے": "सफ़हे", "باب": "बाब", "عنوان": "उनवान", "موضوع": "मौज़ू",
    "خیال": "ख़याल", "خیالات": "ख़यालात", "سوچ": "सोच", "سوچیں": "सोचें",
    "فیصلہ": "फ़ैसला", "فیصلے": "फ़ैसले", "ارادہ": "इरादा", "ارادے": "इरादे",
    "منصوبہ": "मंसूबा", "منصوبے": "मंसूबे", "منصوبہ بندی": "मंसूबाबंदी",
    "کامیابی": "कामयाबी", "کامیابیاں": "कामयाबियां", "ناکامیاں": "नाकामियां",
    "کامیاب ہونا": "कामयाब होना", "ناکام ہونا": "नाकाम होना",
    "محنت کرنا": "मेहनत करना", "کوشش کرنا": "कोशिश करना",
    "ہمت کرنا": "हिम्मत करना", "حوصلہ رکھنا": "हौसला रखना",
    "صبر کرنا": "सब्र करना", "شکر ادا کرنا": "शुक्र अदा करना",
    "دعا کرنا": "दुआ करना", "الله سے مانگنا": "अल्लाह से मांगना",
    "خدا پر بھروسہ": "ख़ुदा पर भरोसा", "رب کی مدد": "रब की मदद",
    "پیار کرنا": "प्यार करना", "محبت کرنا": "मोहब्बत करना",
    "ارمان رکھنا": "अरमान रखना", "خواب دیکھنا": "ख्वाब देखना",
    "حقیقت بنانا": "हक़ीक़त बनाना", "سچ بولنا": "सच बोलना",
    "جھوٹ بولنا": "झूठ बोलना", "حق کی بات": "हक़ की बात",
    "باطل کی بات": "बातिल की बात", "انصاف کرنا": "इंसाफ़ करना",
    "ظلم کرنا": "ज़ुल्म करना", "عدل کرنا": "अदल करना",
    "امان دینا": "अमान देना", "امن قائم کرنا": "अमन क़ायम करना",
    "جنگ لڑنا": "जंग लड़ना", "صلح کرنا": "सुल्ह करना",
    "فتح حاصل کرنا": "फ़तह हासिल करना", "شکست کھانا": "शिकस्त खाना",
    "کامیاب ہونا": "कामयाब होना", "ناکام ہونا": "नाकाम होना",
    "مضبوط بننا": "मज़बूत बनना", "کمزور پڑنا": "कमज़ोर पड़ना",
    "طاقتور بننا": "ताक़तवर बनना", "بے بس ہونا": "बेबस होना",
    "آزاد ہونا": "आज़ाद होना", "غلام بننا": "ग़ुलाम बनना",
    "آزادی حاصل کرنا": "आज़ादी हासिल करना", "غلامی سے نکلنا": "ग़ुलामी से निकलना",
    "ترقی کرنا": "तरक़्क़ी करना", "پسماندگی دور کرنا": "पसमंदगी दूर करना",
    "علم حاصل کرنا": "इल्म हासिल करना", "عمل کرنا": "अमल करना",
    "تجربہ حاصل کرنا": "तज्रिबा हासिल करना", "سبق سیکھنا": "सबक़ सीखना",
    "استاد بننا": "उस्ताद बनना", "شاگرد بننا": "शागिर्द बनना",
    "کتاب پڑھنا": "किताब पढ़ना", "قلم اٹھانا": "क़लम उठाना",
    "خیال رکھنا": "ख़याल रखना", "سوچنا": "सोचना", "فیصلہ کرنا": "फ़ैसला करना",
    "ارادہ کرنا": "इरादा करना", "منصوبہ بنانا": "मंसूबा बनाना",
    "گواہ": "गवाह", "عزت": "इज़्ज़ت", "صحیح": "सही", "ماہوں": "माहों",
    "انسانیت": "इंसानियत", "جوڑنے": "जोड़ने", "کھڑے": "खड़े", "کہرے": "कहरे",
    "بازار": "बाज़ार", "گواہ": "गवाह",

    # Critical words for clean motivational / everyday speech
    "اصل": "असल", "کہ": "कि", "کرن": "किरण", "بکھیرتی": "बिखेरती",
    "ہمیں": "हमें", "یاد": "याद", "دلاتی": "दिलाती", "موقع": "मौका",
    "دوستوں": "दोस्तों", "صحبت": "सोहबत", "بزرگوں": "बुज़ुर्गों",
    "معنوں": "मायनों", "کسی": "किसी", "کریں": "करें", "کیونکہ": "क्योंकि",
    "حاصل": "हासिल", "ان": "उन", "چاہیے": "चाहिए", "خود": "खुद",
    "بھروسہ": "भरोसा", "اکیلا": "अकेला", "بانٹنے": "बांटने",
    "مثبت": "मुस्बत", "رہیں": "रहें", "پہاڑ": "पहाड़", "بڑھتے": "बढ़ते",
    "پہلی": "पहली", "اعمال": "अमाल", "مستقل": "मुस्तक़िल",
    "مزاجی": "मिज़ाजी", "گھبرانا": "घबराना", "اندھیری": "अंधेरी",
    "روشن": "रोशन", "یقین": "यकीन", "طاقت": "ताकत", "روک": "रोक",
    "سکتی": "सकती", "آس": "आस", "پاس": "पास", "تھک": "थक",
    "اپنوں": "अपनों", "خزانہ": "ख़ज़ाना", "کم": "कम", "سوچ": "सोच",
    "شکر": "शुक्र", "ادا": "अदा", "بڑھنے": "बढ़ने", "رہنا": "रहना",
    "کوشش": "कोशिश", "خوبصورت": "खूबसूरत", "ضرور": "ज़रूर",
    "چھوٹے": "छोटे", "اچھے": "अच्छे", "خوابوں": "ख्वाबों",
    "مشکل": "मुश्किल", "وقت": "वक्त", "رات": "रात", "دن": "दिन",
    "دنیا": "दुनिया", "لوگوں": "लोगों", "ساتھ": "साथ", "انسان": "इंसान",
    "آسان": "आसान", "علم": "इल्म", "خوشی": "खुशी", "آگے": "आगे",
    "بڑھتے رہیں": "बढ़ते रहें", "مل کر": "मिल कर", "آس پاس": "आस पास",
    "دن رات": "दिन रात", "ہر حال": "हर हाल", "اصل بات": "असल बात",
    "پہلی کرن": "पहली किरण", "نیا موقع": "नया मौका", "صحیح معنوں": "सही मायनों",
    "مستقل مزاجی": "मुस्तक़िल मिज़ाजी", "اندھیری رات": "अंधेरी रात",
    "روشن دن": "रोशन दिन", "اپنے آپ": "अपने आप", "خود پر": "खुद पर",
    "آگے بڑھنے": "आगे बढ़ने", "مل کر رہیں": "मिल कर रहें",
    "نیا سیکھنے": "नया सीखने", "شکر ادا": "शुक्र अदा",
    "صبح": "सुबह", "روشنی": "रोशनी", "کتابوں": "किताबों",
    "سیکھنا": "सीखना", "محبت": "मोहब्बत", "خلوص": "ख़ुलूस",
    "دلوں": "दिलों", "جوڑنے": "जोड़ने", "مدد": "मदद",
    "کامیابی": "कामयाबी", "محنت": "मेहनत", "خواب": "ख्वाब",
    "دیکھنا": "देखना", "سچ": "सच",

    # Additional commercial / everyday coverage
    "زندگی": "ज़िंदगी", "سفر": "सफ़र", "موڑ": "मोड़", "سبق": "सबक़",
    "راستے": "रास्ते", "آسان": "आसान", "مشکلات": "मुश्किलात", "پہاڑ": "पहाड़",
    "سامنے": "सामने", "کھڑے": "खड़े", "اصل": "असल", "بات": "बात",
    "حال": "हाल", "بڑھتے": "बढ़ते", "رہیں": "रहें", "صبح": "सुबह",
    "پہلی": "पहली", "کرن": "किरण", "روشنی": "रोशनी", "بکھیرتی": "बिखेरती",
    "یاد": "याद", "دلاتی": "दिलाती", "نئی": "नयी", "موقع": "मौका",
    "کتابوں": "किताबों", "سیکھنا": "सीखना", "دوستوں": "दोस्तों",
    "صحبت": "सोहबत", "رہنا": "रहना", "بزرگوں": "बुज़ुर्गों",
    "عزت": "इज़्ज़त", "صحیح": "सही", "معنوں": "मायनों", "انسانیت": "इंसानियत",
    "محبت": "मोहब्बत", "خلوص": "ख़ुलूस", "دلوں": "दिलों", "جوڑنے": "जोड़ने",
    "مدد": "मदद", "ضرور": "ज़रूर", "کریں": "करें", "کیونکہ": "क्योंकि",
    "چھوٹے": "छोटे", "اچھے": "अच्छे", "اعمال": "अमाल", "خوبصورت": "खूबसूरत",
    "کامیابی": "कामयाबी", "حاصل": "हासिल", "محنت": "मेहनत", "مستقل": "मुस्तक़िल",
    "مزاجی": "मिज़ाजी", "ضروری": "ज़रूरी", "خواب": "ख्वाब", "دیکھنا": "देखना",
    "اچھی": "अच्छी", "خوابوں": "ख्वाबों", "سچ": "सच", "دن": "दिन", "رات": "रात",
    "پڑتا": "पड़ता", "مشکل": "मुश्किल", "وقت": "वक्त", "گھبرانا": "घबराना",
    "چاہیے": "चाहिए", "اندھیری": "अंधेरी", "روشن": "रोशन", "آتا": "आता",
    "یقین": "यकीन", "رکھیں": "रखें", "خود": "खुद", "بھروسہ": "भरोसा",
    "ہوتا": "होता", "دنیا": "दुनिया", "طاقت": "ताकत", "بڑھنے": "बढ़ने",
    "روک": "रोक", "سکتی": "सकती", "آس": "आस", "پاس": "पास", "لوگوں": "लोगों",
    "ساتھ": "साथ", "مل": "मिल", "اکیلا": "अकेला", "انسان": "इंसान",
    "جلدی": "जल्दी", "تھک": "थक", "جاتا": "जाता", "اپنوں": "अपनों",
    "ہو": "हो", "جاتی": "जाती", "ہمیشہ": "हमेशा", "کچھ": "कुछ", "نیا": "नया",
    "سیکھنے": "सीखने", "کوشش": "कोशिश", "علم": "इल्म", "خزانہ": "ख़ज़ाना",
    "بانٹنے": "बांटने", "کم": "कम", "سوچ": "सोच", "مثبت": "मुस्बत",
    "رکھیں": "रखें", "چھوٹی": "छोटी", "خوشی": "खुशी", "شکر": "शुक्र",
    "ادا": "अदा", "آگے": "आगे",
    "لیکن": "लेकिन", "اگر": "अगर", "آپ": "आप", "کسی": "किसी",
    "ہیں": "हैं", "ہے": "है", "کا": "का", "کی": "की", "کے": "के",
    "کو": "को", "میں": "में", "سے": "से", "پر": "पर", "اور": "और",
    "تو": "तो", "جو": "जो", "یہ": "यह", "وہ": "वह", "ہر": "हर",
    "ایک": "एक", "ایسا": "ऐसा", "ایسی": "ऐसी", "ایسے": "ऐसे",

    # Expanded commercial vocabulary
    "کامیابی": "कामयाबी", "راہ": "राह", "ہمیشہ": "हमेशा", "آسان": "आसान",
    "کئی": "कई", "بار": "बार", "تھک": "थक", "مایوس": "मायूस",
    "سوچنے": "सोचने", "لگتا": "लगता", "شاید": "शायद", "بڑھنا": "बढ़ना",
    "ممکن": "मुमक़िन", "حقیقت": "हक़ीक़त", "بڑی": "बड़ी", "کوششوں": "कोशिशों",
    "جنم": "जनम", "لیتی": "लेती", "مسلسل": "मुसलसल", "صبر": "सब्र",
    "مقصد": "मक़सद", "نظر": "नज़र", "منزل": "मंज़िल", "قریب": "क़रीब",
    "سویرے": "सवेरे", "کتابیں": "किताबें", "پڑھنا": "पढ़ना", "بدل": "बदल",
    "سکتا": "सकता", "قدر": "क़दर", "سچا": "सच्चा", "ادھورا": "अधूरा",
    "چھوڑیں": "छोड़ें", "ہاریں": "हारें", "ناکامی": "नाकामी", "سکھاتی": "सिखाती",
    "مضبوط": "मज़बूत", "بناتا": "बनाता", "صلاحیتوں": "सलाहियतों",
    "کرتا": "करता", "کرتی": "करती", "کرتے": "करते", "کریں": "करें",
    "رہنا": "रहना", "رہتے": "रहते", "رہتی": "रहती", "آنا": "आना",
    "جانا": "जाना", "دینا": "देना", "لینا": "लेना", "ہونا": "होना",
    "ملنا": "मिलना", "بننا": "बनना", "پڑنا": "पड़ना", "سکنا": "सकना",
    "چاہتا": "चाहता", "چاہتی": "चाहती", "چاہتے": "चाहते",
    "رکھتا": "रखता", "رکھتی": "रखती", "رکھتے": "रखते",
    "سمجھتا": "समझता", "سمجھتی": "समझती", "سمجھتے": "समझते", "سمجھنا": "समझना",
    "سوچتا": "सोचता", "سوچتی": "सोचती", "سوچتے": "सोचते", "سوچنا": "सोचना",
    "بولتا": "बोलता", "بولتی": "बोलती", "بولتے": "बोलते", "بولنا": "बोलना",
    "سنتا": "सुनता", "سنتی": "सुनती", "سنتے": "सुनते", "سننا": "सुनना",
    "دیکھتا": "देखता", "دیکھتی": "देखती", "دیکھتے": "देखते",
    "پڑھتا": "पढ़ता", "پڑھتی": "पढ़ती", "پڑھتے": "पढ़ते",
    "لکھتا": "लिखता", "لکھتی": "लिखती", "لکھتے": "लिखते", "لکھنا": "लिखना",
    "چلتا": "चलता", "چلتی": "चलती", "چلتے": "चलते", "چلنا": "चलना",
    "گھبراتا": "घबराता", "گھبراتی": "घबराती", "گھبراتے": "घबराते",
    "دنیا": "दुनिया", "آدمی": "आदमी", "عورت": "औरत", "بچہ": "बच्चा",
    "گھر": "घर", "شہر": "शहर", "ملک": "मुल्क", "پیسہ": "पैसा",
    "خوشی": "खुशी", "غم": "ग़म", "دکھ": "दुख", "درد": "दर्द",
    "امید": "उम्मीद", "خوف": "ख़ौफ़", "حوصلہ": "हौसला", "ایمان": "ईमान",
    "جھوٹ": "झूठ", "حق": "हक़", "باطل": "बातिल", "انصاف": "इंसाफ़",
    "ظلم": "ज़ुल्म", "امن": "अमन", "جنگ": "जंग", "فتح": "फ़तह",
    "کامیاب": "कामयाब", "ناکام": "नाकाम", "کمزور": "कमज़ोर",
    "برا": "बुरा", "بڑا": "बड़ा", "چھوٹا": "छोटा", "پرانا": "पुराना",
    "تیز": "तेज़", "آہستہ": "आहिस्ता", "دیر": "देर", "پہلے": "पहले",
    "پرسوں": "परसों", "ابھی": "अभी", "اکثر": "अक्सर", "تھوڑا": "थोड़ा",
    "زیادہ": "ज़्यादा", "بلکل": "बिल्कुल", "مگر": "मगर",
    "اس لیے": "इस लिए", "کے بارے": "के बारे", "کے ساتھ": "के साथ",
    "کے بعد": "के बाद", "کے پہلے": "के पहले", "کی وجہ": "की वजह",
    "کی طرح": "की तरह", "جن": "जिन", "یہی": "यही", "وہی": "वही",
    "کیسا": "कैसा", "کیسی": "कैसी", "کتنا": "कितना", "کتنی": "कितनी",
    "کتنے": "कितने",

    # Words that were falling through to the generic fallback converter
    # and coming out garbled — added after listening-test feedback flagged
    # them specifically (مختصر/مسکرائیے/حیرت/صاف all had no dictionary
    # entry at all, so fallback_native_to_devanagari's generic schwa
    # insertion was producing spellings the acoustic model had never
    # seen in training).
    "مختصر": "मुख़्तसर", "صاف": "साफ़", "حیرت": "हैरत",
    "حیرت انگیز": "हैरत अंगेज़", "مسکرائیے": "मुस्कुराइए", "مسکراہٹ": "मुस्कुराहट",
}

# Digraphs must be replaced before single chars
URDU_DIGRAPHS = {
    "بھ": "भ", "پھ": "फ", "تھ": "थ", "ٹھ": "ठ", "جھ": "झ",
    "چھ": "छ", "دھ": "ध", "ڈھ": "ढ", "کھ": "ख", "گھ": "घ",
    "ڑھ": "ढ़",
}

# Single character map (used after digraph replacement)
URDU_CHAR_MAP = {
    "ا": "अ", "آ": "आ", "ب": "ब", "پ": "प", "ت": "त", "ٹ": "ट", "ث": "स",
    "ج": "ज", "چ": "च", "ح": "ह", "خ": "ख़", "د": "द", "ڈ": "ड", "ذ": "ज़",
    "ر": "र", "ڑ": "ड़", "ز": "ज़", "ژ": "झ़", "س": "स", "ش": "श", "ص": "स",
    "ض": "ज़", "ط": "त", "ظ": "ज़", "ع": "अ", "غ": "ग़", "ف": "फ़", "ق": "क़",
    "ک": "क", "گ": "ग", "ل": "ल", "م": "म", "ن": "न", "ں": "ं", "و": "व",
    "ہ": "ह", "ھ": "ह", "ی": "य", "ے": "ए", "۔": "।", "؟": "?", "ئ": "य",
    "ء": "", "ؤ": "व", "أ": "अ", "إ": "इ", "ة": "ह", "ۀ": "ह",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
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
    r"\bkhas\b": "khaas", r"\baisa\b": "aisa", r"\baisi\b": "aisi", r"\baise\b": "aise",
    r"\bkya\b": "kya", r"\bkyun\b": "kyun", r"\bkahan\b": "kahaan",
    r"\bkaisa\b": "kaisa", r"\bkaise\b": "kaise", r"\bkaisi\b": "kaisi",
}

ROMAN_TO_DEVANAGARI_WORDS = {
    # Core function words
    "ki": "की", "ka": "का", "ke": "के", "ko": "को", "bhi": "भी", "kal": "कल",
    "yeh": "यह", "woh": "वह", "tha": "था", "thi": "थी", "the": "थे",
    "hai": "है", "hain": "हैं", "ho": "हो", "hona": "होना", "chahiye": "चाहिए",
    "na": "ना", "nahi": "नहीं", "lekin": "लेकिन", "jis": "जिस", "aur": "और",
    "to": "तो", "agar": "अगर", "phir": "फिर", "ab": "अब", "tab": "तब",
    "kab": "कब", "kahan": "कहाँ", "kahaan": "कहाँ", "kyun": "क्यों", "kyunke": "क्योंकि",
    "kaise": "कैसे", "kaisa": "कैसा", "kaisi": "कैसी", "kaun": "कौन", "kya": "क्या",
    "haan": "हाँ", "sirf": "सिर्फ़", "bahut": "बहुत", "kuch": "कुछ", "sab": "सब",
    "har": "हर", "koi": "कोई", "sabhi": "सभी", "mein": "में", "se": "से", "par": "पर",
    "liye": "लिए", "ke liye": "के लिए", "wala": "वाला", "wali": "वाली", "wale": "वाले",

    # Core vocabulary
    "zindagi": "ज़िंदगी", "khas": "खास", "khaas": "खास", "tohfa": "तोहफा",
    "hum": "हम", "khush": "खुश", "chhoti": "छोटी", "khushiyan": "खुशियां",
    "maani": "मानी", "deti": "देती", "deta": "देता", "dete": "देते",
    "subah": "सुबह", "jaldi": "जल्दी", "uthna": "उठना", "ek": "एक",
    "achhi": "अच्छी", "achha": "अच्छा", "achhe": "अच्छे", "aadat": "आदत",
    "is": "इस", "din": "दिन", "banta": "बनता", "banti": "बनती", "banate": "बनाते",
    "kitabon": "किताबों", "kitab": "किताब", "ilm": "इल्म", "insan": "इंसान",
    "taakat": "ताकत", "hamesha": "हमेशा", "naya": "नया", "nayi": "नयी",
    "seekhna": "सीखना", "seekhne": "सीखने", "jahan": "जहां", "khulta": "खुलता",
    "khula": "खुला", "baatein": "बातें", "samajhta": "समझता", "samajh": "समझ",
    "aasan": "आसान", "pasand": "पसंद", "dosti": "दोस्ती", "banati": "बनाती",
    "dost": "दोस्त", "saath": "साथ", "mushkil": "मुश्किल", "waqt": "वक्त",
    "hi": "ही", "kaam": "काम", "aate": "आते", "aata": "आता", "aati": "आती",
    "mohabbat": "मोहब्बत", "khuluus": "ख़ुलूस", "dilon": "दिलों", "milati": "मिलाती",
    "logon": "लोगों", "madad": "मदद", "dena": "देना", "amal": "अमल", "dil": "दिल",
    "hota": "होता", "hoti": "होती", "hote": "होते", "umeed": "उम्मीद",
    "aage": "आगे", "le": "ले", "jaati": "जाती", "jaata": "जाता", "jaate": "जाते",
    "khwab": "ख्वाब", "dekhna": "देखना", "baat": "बात", "khwabon": "ख्वाबों",
    "sach": "सच", "banane": "बनाने", "mehnat": "मेहनत", "kabhi": "कभी",
    "zaya": "ज़ाया", "insanon": "इंसानों", "khasiyat": "खासियत",
    "apne": "अपने", "aap": "आप", "yakeen": "यकीन", "ahem": "अहम",
    "himmat": "हिम्मत", "milti": "मिलती", "milta": "मिलता", "milte": "मिलते",
    "kaamyabi": "कामयाबी", "mustaqil": "मुस्तक़िल", "mizaji": "मिज़ाजी",
    "soch": "सोच", "musbat": "मुस्बत", "fayda": "फ़ायदा", "dono": "दोनों",
    "halaton": "हालतों", "sukoon": "सुकून", "faisle": "फैसले",
    "mustaqbil": "मुस्तक़बिल", "aaj": "आज", "phal": "फल", "sachai": "सच्चाई",
    "maloom": "मालूम", "honi": "होनी", "saathi": "साथी", "taleem": "तालीम",
    "neemat": "नेमत", "ustad": "उस्ताद", "talib": "तालिब", "ilmon": "इल्मों",
    "badal": "बदल", "tanha": "तन्हा", "neki": "नेकी", "badla": "बदला",
    "khidmat": "ख़िदमत", "log": "लोग", "achhai": "अच्छाई", "nekiyan": "नेकियां",
    "khushi": "खुशी", "barhata": "बढ़ाता", "safar": "सफ़र", "mor": "मोड़",
    "sabaq": "सबक़", "raste": "रास्ते", "mushkilat": "मुश्किलात", "samne": "सामने",
    "haal": "हाल", "kiran": "किरण", "roshni": "रोशनी", "bikherte": "बिखेरती",
    "bikhertee": "बिखेरती", "hameen": "हमें", "hamein": "हमें", "yaad": "याद",
    "dilati": "दिलाती", "mauqa": "मौका", "doston": "दोस्तों", "suhbat": "सोहबत",
    "buzurgon": "बुज़ुर्गों", "izzat": "इज़्ज़त", "karna": "करना", "karne": "करने",
    "karta": "करता", "karti": "करती", "karte": "करते", "kiya": "किया", "kiye": "किए",
    "gaya": "गया", "gayi": "गई", "gaye": "गए", "hua": "हुआ", "hui": "हुई", "hue": "हुए",
    "raha": "रहा", "rahi": "रही", "rahe": "रहे", "ja": "जा", "aa": "आ", "de": "दे",
    "dekho": "देखो", "suno": "सुनो", "padho": "पढ़ो", "likho": "लिखो", "bolo": "बोलो",
    "chalo": "चलो", "rakho": "रखो", "khubsurat": "खूबसूरत", "zaroori": "ज़रूरी",
    "zaroor": "ज़रूर", "raat": "रात", "shaam": "शाम", "duniya": "दुनिया",
    "aasmaan": "आसमान", "zameen": "ज़मीन", "paani": "पानी", "aag": "आग", "hawa": "हवा",
    "andhera": "अंधेरा", "andheri": "अंधेरी", "gham": "ग़म", "nafrat": "नफ़रत",
    "dushmani": "दुश्मनी", "naakami": "नाकामी", "koshish": "कोशिश", "hausla": "हौसला",
    "sabr": "सब्र", "shukr": "शुक्र", "dua": "दुआ", "allah": "अल्लाह", "khuda": "ख़ुदा",
    "rab": "रब", "pyaar": "प्यार", "arman": "अरमान", "haqeeqat": "हक़ीक़त",
    "jhoot": "झूठ", "haq": "हक़", "batil": "बातिल", "insaf": "इंसाफ़", "zulm": "ज़ुल्म",
    "adl": "अदल", "aman": "अमन", "jang": "जंग", "sulh": "सुल्ह", "fatah": "फ़तह",
    "shikast": "शिकस्त", "kaamyab": "कामयाब", "naakam": "नाकाम", "mazboot": "मज़बूत",
    "kamzor": "कमज़ोर", "taqatwar": "ताक़तवर", "bebas": "बेबस", "azaad": "आज़ाद",
    "ghulam": "ग़ुलाम", "azaadi": "आज़ादी", "ghulami": "ग़ुलामी", "taraqqi": "तरक़्क़ी",
    "ilm": "इल्म", "tajruba": "तज्रिबा", "shagird": "शागिर्द", "qalam": "क़लम",
    "kaghaz": "काग़ज़", "safha": "सफ़हा", "unwan": "उनवान", "mauzoo": "मौज़ू",
    "khayal": "ख़याल", "irada": "इरादा", "mansuba": "मंसूबा",
    "aisa": "ऐसा", "aisi": "ऐसी", "aise": "ऐसे", "wahan": "वहाँ", "yahan": "यहाँ",
    "ghabrana": "घबराना", "baad": "बाद", "roshan": "रोशन", "rakhein": "रखिए",
    "khud": "खुद", "bharosa": "भरोसा", "rok": "रोक", "mil": "मिल", "rahein": "रहें",
    "akela": "अकेला", "thak": "थक", "khazana": "ख़ज़ाना", "baantne": "बांटने",
    "ada": "अदा", "mayno": "मायनों", "insaniyat": "इंसानियत", "jodne": "जोड़ने",
    "kisi": "किसी", "sakte": "सकते", "karen": "करें",
    "chhote": "छोटे", "chhoti": "छोटी", "chhota": "छोटा", "ache": "अच्छे",
    "achi": "अच्छी", "acha": "अच्छा", "hasil": "हासिल", "padta": "पड़ता",
    "padti": "पड़ती", "padte": "पड़ते", "gawah": "गवाह", "sahi": "सही",
    "maynon": "मायनों", "jodne": "जोड़ने", "joden": "जोड़ें",
    "kahre": "कहरे", "khade": "खड़े", "bazaar": "बाज़ार", "bazar": "बाज़ार",
    "gawah": "गवाह", "sahih": "सही", "sahih": "सहीह",
    "insaniyat": "इंसानियत", "jo": "जो", "woh": "वह", "un": "उन",
    "din": "दिन", "raat": "रात", "ek": "एक", "karna": "करना",
    "jisme": "जिसमें", "jismen": "जिसमें", "jis": "जिस",
    "aa": "आ", "khade": "खड़े", "hote": "होते", "hain": "हैं",
    "lekin": "लेकिन", "apne": "अपने", "ki": "की", "hi": "ही",
    "mein": "में", "hai": "है", "aur": "और", "ko": "को",
    "ka": "का", "kaam": "काम", "karte": "करते", "agar": "अगर",
    "aap": "आप", "ki": "की", "to": "तो", "kyunke": "क्योंकि",
    "hi": "ही", "ko": "को", "banate": "बनाते", "ke": "के",
    "liye": "लिए", "aur": "और", "sabse": "सबसे", "hain": "हैं",
    "dekhna": "देखना", "achhi": "अच्छी", "baat": "बात",
    "un": "उन", "ko": "को", "ke": "के", "liye": "लिए",
    "din": "दिन", "raat": "रात", "ek": "एक", "bhi": "भी",
    "se": "से", "nahi": "नहीं", "chahiye": "चाहिए",
}


def _is_urdu_consonant(ch: str) -> bool:
    return ch in "بپتٹثجچحخدڈذرڑزژسشصضطظعغفقکگلمنوہھی"


def _is_dev_consonant(ch: str) -> bool:
    # Devanagari consonants + nukta forms
    return ("\u0915" <= ch <= "\u0939") or ch in "क़ख़ग़ज़झ़ड़ढ़फ़"


def fallback_native_to_devanagari(word: str) -> str:
    """
    Robust sequential transliterator for native Urdu script → Devanagari.
    Handles digraphs, contextual vowels (و ی ے ا آ), nasal ں, and inserts
    implicit schwa between consonants for natural Hindi pronunciation.
    """
    if not word:
        return ""

    # 1. Replace aspirated digraphs first (longest match)
    w = word
    for dig, repl in sorted(URDU_DIGRAPHS.items(), key=lambda x: -len(x[0])):
        w = w.replace(dig, repl)

    # 2. Sequential conversion with vowel context
    result = []
    i = 0
    n = len(w)
    prev_was_consonant = False

    while i < n:
        ch = w[i]

        # Already converted digraph characters (Devanagari)
        if _is_dev_consonant(ch) or ch in "अआइईउऊएऐओऔंःँ":
            result.append(ch)
            prev_was_consonant = _is_dev_consonant(ch)
            i += 1
            continue

        # Nasalisation
        if ch == "ں":
            result.append("ं")
            prev_was_consonant = False
            i += 1
            continue

        # Long / independent vowels & matras
        if ch == "آ":
            if prev_was_consonant:
                result.append("ा")
            else:
                result.append("आ")
            prev_was_consonant = False
            i += 1
            continue

        if ch == "ا":
            # ا after consonant -> ा ; at start of word (or after a vowel) -> अ
            if prev_was_consonant:
                result.append("ा")
            else:
                result.append("अ")
            prev_was_consonant = False
            i += 1
            continue

        if ch == "و":
            next_ch = w[i + 1] if i + 1 < n else ""
            # و + ا is the common causative/agentive pattern (کرواتے,
            # دکھوانا, والی...) where و is consonant /v/, not the vowel /o/.
            # Was falling into the vowel branch below, producing nonsense
            # like کرواتے -> "करोअते" instead of "करवाते".
            if next_ch == "ا":
                result.append("वा")
                prev_was_consonant = False
                i += 2
                continue
            # و after consonant → ो / ू / व ; at start → व / ओ
            if prev_was_consonant:
                # Prefer ो for most cases (common in Urdu→Hindi)
                result.append("ो")
                prev_was_consonant = False
            else:
                result.append("व")
                # BUG FIX: व is a real Devanagari consonant — this was
                # unconditionally set to False here, so the very next
                # character (often ا) always treated itself as word-start
                # rather than "after a consonant", turning वाली into वअली.
                prev_was_consonant = True
            i += 1
            continue

        if ch == "ی":
            if prev_was_consonant:
                result.append("ी")
            else:
                result.append("य")
            prev_was_consonant = False
            i += 1
            continue

        if ch == "ے":
            if prev_was_consonant:
                result.append("े")
            else:
                result.append("ए")
            prev_was_consonant = False
            i += 1
            continue

        if ch == "ئ" or ch == "ء":
            # hamza – usually silent or slight ی
            if not prev_was_consonant:
                result.append("य")
            prev_was_consonant = False
            i += 1
            continue

        if ch == "ع":
            # ain has no Devanagari equivalent — three distinct behaviours
            # depending on position, previously collapsed into a single
            # "always emit अ" rule that added a spurious extra syllable in
            # the (very common) mid-word case, e.g. معمولی -> "मअमोली"
            # instead of "ममोली", معیشت -> "मऐशत" instead of "मीशत".
            next_ch = w[i + 1] if i + 1 < n else ""
            if next_ch == "ا":
                result.append("आ")
                prev_was_consonant = False
                i += 2
                continue
            if next_ch in "یے":
                result.append("ई")
                prev_was_consonant = False
                i += 2
                continue
            if next_ch == "و":
                result.append("ऊ")
                prev_was_consonant = False
                i += 2
                continue
            if prev_was_consonant:
                # Mid-word, no following vowel letter: functions as a bare
                # glottal separator with no real vowel of its own in casual
                # Hindi-ized pronunciation — elide rather than invent a
                # syllable. Leave prev_was_consonant as-is (pass-through).
                i += 1
                continue
            # Word-initial (or after a vowel) with no diacritics to tell us
            # the real vowel quality — best-effort default.
            result.append("अ")
            prev_was_consonant = False
            i += 1
            continue

        # Regular consonants via map
        if ch in URDU_CHAR_MAP:
            mapped = URDU_CHAR_MAP[ch]
            # Insert schwa if previous was also a consonant (and mapped is consonant)
            if prev_was_consonant and _is_dev_consonant(mapped):
                # Avoid double schwa; only insert if helpful
                # Common rule: insert अ between two consonants unless cluster is preferred
                pass  # We keep it tight for TTS clarity; schwa is often implicit in speech
            result.append(mapped)
            prev_was_consonant = _is_dev_consonant(mapped) or mapped in "क़ख़ग़ज़झ़ड़ढ़फ़"
            i += 1
            continue

        # Unknown / punctuation – pass through
        result.append(ch)
        prev_was_consonant = False
        i += 1

    out = "".join(result)

    # 3. Post-cleanup of common artefacts
    # Two or more consecutive independent अ within one word represent a real
    # long vowel (e.g. ع + ا in عادت -> "aa-dat"), not accidental duplication.
    # Merge into आ rather than collapsing to a single short अ.
    out = re.sub(r"अ{2,}", "आ", out)
    # Fix अय → ऐ / ए patterns that appear from ا + ی
    out = out.replace("अय", "ऐ")
    out = out.replace("आय", "आय")  # keep
    # Clean double matras
    out = re.sub(r"([ाीूेैोौं])\1+", r"\1", out)

    return out


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
        # Longer digraphs / trigraphs first
        ("chh", "छ"), ("khh", "ख्ख"), ("ghh", "घ्घ"),
        ("kh", "ख़"), ("gh", "ग़"), ("sh", "श"), ("ch", "च"),
        ("jh", "झ"), ("bh", "भ"), ("ph", "फ"), ("th", "थ"),
        ("dh", "ध"), ("rh", "ढ़"), ("zh", "झ़"), ("ck", "क"),
        ("ng", "ंग"), ("ny", "ञ"), ("tt", "ट"), ("dd", "ड"),
        ("rr", "ड़"), ("ll", "ल्ल"), ("mm", "म्म"), ("nn", "न्न"),
        ("ss", "स्स"), ("pp", "प्प"), ("bb", "ब्ब"),
        ("b", "ब"), ("c", "क"), ("d", "द"), ("f", "फ़"), ("g", "ग"),
        ("h", "ह"), ("j", "ज"), ("k", "क"), ("l", "ल"), ("m", "म"),
        ("n", "न"), ("p", "प"), ("q", "क़"), ("r", "र"), ("s", "स"),
        ("t", "त"), ("v", "व"), ("w", "व"), ("x", "क्स"), ("y", "य"), ("z", "ज़")
    ]

    # Vowels: (roman, independent_char, matra_char)
    # Longer matches first
    VOWEL_MAP = [
        ("ein", "एं", "ें"), ("aan", "आन", "ां"), ("oon", "ऊं", "ूं"), ("on", "ओं", "ों"),
        ("aai", "आई", "ाई"), ("aau", "आऊ", "ाऊ"), ("ayi", "अयी", "यी"),
        ("aa", "आ", "ा"), ("ee", "ई", "ी"), ("oo", "ऊ", "ू"),
        ("ai", "ऐ", "ै"), ("au", "औ", "ौ"), ("ie", "इए", "िए"),
        ("ey", "ए", "े"), ("ay", "ए", "े"),
        ("a", "अ", ""),   ("e", "ए", "े"),  ("i", "इ", "ि"),
        ("o", "ओ", "ो"),  ("u", "उ", "ु")
    ]

    tokens = []
    i = 0
    n = len(w)

    while i < n:
        matched = False

        # Match nasal ending 'n' (when not followed by vowel)
        if w[i] == "n" and (i == n - 1 or (i < n - 1 and w[i + 1] not in "aeiouy")):
            tokens.append(("NASAL", "ं"))
            i += 1
            continue

        # Match consonants (longest first already sorted)
        for roman, dev in CONSONANT_MAP:
            if w.startswith(roman, i):
                tokens.append(("CONSONANT", dev))
                i += len(roman)
                matched = True
                break
        if matched:
            continue

        # Match vowels
        for roman, indep, matra in VOWEL_MAP:
            if w.startswith(roman, i):
                tokens.append(("VOWEL", (indep, matra)))
                i += len(roman)
                matched = True
                break
        if matched:
            continue

        tokens.append(("OTHER", w[i]))
        i += 1

    # Assemble Devanagari string from parsed tokens
    res = []
    prev_type = None

    for token_type, val in tokens:
        if token_type == "CONSONANT":
            res.append(val)
            prev_type = "CONSONANT"
        elif token_type == "VOWEL":
            indep, matra = val
            if prev_type == "CONSONANT":
                # Attach matra; empty matra for short 'a' means inherent schwa (do nothing)
                if matra:
                    res.append(matra)
            else:
                res.append(indep)
            prev_type = "VOWEL"
        elif token_type == "NASAL":
            res.append(val)
            prev_type = "NASAL"
        else:
            res.append(val)
            prev_type = token_type

    return "".join(res)


def transliterate_urdu_script_to_devanagari(text: str) -> str:
    tokens = re.split(r"(\s+|[.,!?۔؟،؛—\-\"'():;«»])", text)
    n = len(tokens)
    word_positions = [idx for idx, t in enumerate(tokens) if t.strip()]
    result = list(tokens)

    MAX_PHRASE_WORDS = 3  # matches longest existing multi-word dict entry
    wi = 0
    wp_len = len(word_positions)
    while wi < wp_len:
        matched = False
        max_span = min(MAX_PHRASE_WORDS, wp_len - wi)
        for wcount in range(max_span, 1, -1):
            span_positions = word_positions[wi:wi + wcount]
            phrase = " ".join(tokens[p].strip() for p in span_positions)
            if phrase in URDU_SCRIPT_WORD_MAP:
                first, last = span_positions[0], span_positions[-1]
                result[first] = URDU_SCRIPT_WORD_MAP[phrase]
                for p in range(first + 1, last + 1):
                    result[p] = ""  # consumed word tokens + separators between them
                wi += wcount
                matched = True
                break
        if matched:
            continue

        idx = word_positions[wi]
        clean_token = tokens[idx].strip()
        if clean_token in URDU_SCRIPT_WORD_MAP:
            result[idx] = URDU_SCRIPT_WORD_MAP[clean_token]
        else:
            result[idx] = fallback_native_to_devanagari(clean_token)
        wi += 1

    return "".join(result)


def fix_roman_urdu_misspellings(text: str) -> str:
    cleaned_text = text
    for pattern, replacement in ROMAN_URDU_FIXES.items():
        cleaned_text = re.sub(pattern, replacement, cleaned_text, flags=re.IGNORECASE)
    return cleaned_text


def transliterate_roman_to_devanagari(text: str) -> str:
    tokens = re.split(r"(\s+|[.,!?۔؟،؛—\-\"'():;«»])", text)
    result = []
    for token in tokens:
        lower_token = token.lower().strip()
        if not lower_token:
            result.append(token)
            continue
        if lower_token in ROMAN_TO_DEVANAGARI_WORDS:
            result.append(ROMAN_TO_DEVANAGARI_WORDS[lower_token])
        elif lower_token.isalpha():
            result.append(fallback_roman_to_devanagari(lower_token))
        else:
            result.append(token)
    return "".join(result)



def _cleanup_devanagari(text: str) -> str:
    """Fix common residual artefacts after rule-based conversion."""
    replacements = [
        ("हे،", "है,"), ("हे।", "है।"), (" हे ", " है "), ("हे,", "है,"),
        ("हीं", "हैं"), ("रखीं", "रखें"), ("करीं", "करें"),
        ("रहीं", "रहें"), ("रहैं", "रहें"), ("नहैं", "नहीं"),
        ("चाहीए", "चाहिए"), ("बअद", "बाद"),
        ("मल कर", "मिल कर"), ("यअद", "याद"), ("मोक़अ", "मौका"),
        ("कीवनकह", "क्योंकि"), ("कह ", "कि "),
        ("ہے", "है"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = text.replace("रहीं", "रहें").replace("करहीं", "करें")
    return text

def prepare_text_for_tts(text: str) -> tuple[str, str]:
    """
    Universal entry point.
    Detects native Urdu script vs Roman Urdu and returns clean Devanagari + language_id.
    """
    if not text or not text.strip():
        return "", "en"

    has_urdu_script = bool(re.search(r"[\u0600-\u06FF]", text))
    if has_urdu_script:
        return _cleanup_devanagari(transliterate_urdu_script_to_devanagari(text.strip())), "hi"

    cleaned_text = fix_roman_urdu_misspellings(text)
    return _cleanup_devanagari(transliterate_roman_to_devanagari(cleaned_text).strip()), "hi"
