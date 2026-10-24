"""Language detection, normalisation and the concept lexicon (rule-based, no ML)."""
from __future__ import annotations

import re
import unicodedata

from ..schemas.internal import FactStatus

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
HINGLISH_MARKERS = {
    "ko", "hai", "hain", "ka", "ki", "ke", "ghar", "pe", "par", "me", "mein", "nahi", "chahiye", "bukhar",
    "khansi", "dard", "papa", "mummy", "maa", "dadaji", "dadi", "bacche", "bachcha", "karwana", "karna",
    "karni", "hai", "ho", "raha", "rahi", "rahe", "aur", "se", "tak", "kal", "subah", "lagwana", "baat",
    "kamzor", "wo", "achanak", "gir", "gaye", "dikhana", "do", "din", "bhi", "mujhe", "unko", "unhe",
}

# Common romanised-Hindi spelling variants -> one canonical token.
SPELLING = {
    "sans": "saans", "saas": "saans", "sanse": "saans", "sine": "seene", "seena": "seene", "sina": "seene",
    "bukhaar": "bukhar", "bukar": "bukhar", "khasi": "khansi", "khaansi": "khansi", "dikat": "dikkat",
    "takleef": "taklif", "nai": "nahi", "nahin": "nahi", "nhi": "nahi", "nahee": "nahi", "mein": "me",
    "main": "me", "behoshi": "behosh", "khun": "khoon", "kamjor": "kamzor", "kamjori": "kamzori",
}

COPULA = {"hai", "hain", "h", "tha", "thi", "hua", "hui", "is", "are", "was", "ho"}
NEG_BEFORE = {"no", "not", "without", "never", "denies", "bina", "बिना"}
NEG_AFTER = {"nahi", "no", "not", "never", "absent", "नहीं", "नही"}

_PREFIX = re.compile(r"^\s*(?:a |my )?(?:family member|relative|myself|someone else|self)\s*:\s*", re.I)


def strip_prefix(text: str) -> str:
    return _PREFIX.sub("", text, count=1)


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).lower()
    t = re.sub(r"[​-‍﻿]", "", t)
    t = re.sub(r"[^\w\sऀ-ॿ']", " ", t)
    tokens = [SPELLING.get(tok, tok) for tok in t.split()]
    return " ".join(tokens)


def detect_language(text: str) -> str:
    if DEVANAGARI.search(text):
        return "hi"
    tokens = set(normalize(text).split())
    if len(tokens & HINGLISH_MARKERS) >= 2 or ("ghar" in tokens) or ("chahiye" in tokens):
        return "hinglish"
    return "en"


def resolve_language(mode: str, *texts: str) -> str:
    m = {"en": "en", "english": "en", "hi": "hi", "hindi": "hi", "hinglish": "hinglish"}.get(mode)
    if m:
        return m
    # auto: prefer the most expressive script seen across the conversation
    detected = [detect_language(t) for t in texts if t]
    for pref in ("hi", "hinglish"):
        if pref in detected:
            return pref
    return "en"


def is_negated(text: str, start: int, end: int) -> bool:
    """Conservative negation: only an immediate cue counts. When unsure, do NOT negate."""
    before = text[:start].split()[-1:]
    after = text[end:].split()[:2]
    if before and before[-1] in NEG_BEFORE:
        return True
    i = 1 if after and after[0] in COPULA else 0
    return i < len(after) and after[i] in NEG_AFTER


# --- concept lexicon --------------------------------------------------------
# id -> (group, regex). Matched on normalised text.
_F = r"(?:\S+ ){0,3}"
CONCEPTS: dict[str, tuple[str, str]] = {
    # symptoms / complaints
    "fever": ("symptom", r"\bfever\b|\btemperature\b|\bbukhar\b|बुखार|\bताप\b"),
    "cough": ("symptom", r"\bcough|\bkhansi\b|खांसी|खाँसी|खासी"),
    "weakness": ("symptom", r"\bweak(?:ness)?\b|\bkamzor(?:i)?\b|कमज़?ोर|कमज़?ोरी"),
    "pain": ("symptom", r"\bpain\b|\bdard\b|दर्द"),
    "stomach_upset": ("symptom", r"vomit|\bulti\b|उल्टी|diarrh?oea|loose motion|\bdast\b|दस्त|acidity|\bgas\b|एसिडिटी|गैस"),
    "bp_sugar_check": ("symptom", r"\bbp\b|blood pressure|बीपी|बी पी"),
    "home_visit_request": ("context", r"\bghar\b|\bat home\b|\bhome (?:visit|check|collection|sample)\b|\bhome\b|घर"),
    # nursing procedures
    "injection": ("nursing", r"inject|इंजेक्शन|insulin|इंसुलिन|इन्सुलिन"),
    "dressing": ("nursing", r"dressing|bandage|bedsore|\bwound\b|\bpatti\b|\bghaav\b|\bghav\b|stitch|पट्टी|घाव|ड्रेसिंग"),
    "catheter": ("nursing", r"catheter|कैथेटर"),
    "iv_drip": ("nursing", r"\biv\b|\bdrip\b|saline|ड्रिप"),
    "nebulization": ("nursing", r"nebuli[sz]|नेबुलाइ"),
    # lab
    "lab_test": ("lab", r"blood test|lab test|urine test|pathology|khoo?n ki ja+n?ch|blood ki ja+n?ch|खून की (?:जांच|जाँच)|ब्लड टेस्ट|पेशाब की (?:जांच|जाँच)|\btests?\b|\bcbc\b|thyroid|lipid|hba1c|full body|\bsample\b|\bculture\b|टेस्ट|सैंपल|थायराइड|फुल बॉडी"),
    # consult
    "consult": ("consult", r"consult|\bsalah\b|सलाह|opinion|ओपिनियन|talk to (?:a |the |my )?doctor|speak to (?:a |the )?doctor|doctor (?:se|ko) (?:baat|bat)|doctor se consult|doctor online|online doctor|online|video (?:call|consult)|teleconsult|baat karni|बात करनी|ऑनलाइन|डॉक्टर से (?:\S+ )?(?:बात|सलाह)|doctor ko (?:\S+ )?dikha|show (?:\S+ ){0,2}to (?:a |the )?doctor|डॉक्टर को (?:\S+ )?दिखा"),
    "report_review": ("consult", r"\breports?\b|रिपोर्ट|prescription"),
}
_COMPILED = {k: (g, re.compile(unicodedata.normalize("NFKC", p))) for k, (g, p) in CONCEPTS.items()}

# concept -> any-of skill groups a caregiver must satisfy (list of alternative sets)
REQUIRED_SKILLS: dict[str, list[set[str]]] = {
    "injection": [{"injection_im", "injection_iv"}],
    "dressing": [{"wound_dressing"}],
    "catheter": [{"catheter_care"}],
    "iv_drip": [{"injection_iv"}],
    "nebulization": [{"nebulization"}],
    "bp_sugar_check": [{"bp_sugar_check", "vitals_monitoring"}],
    "lab_test": [{"sample_collection", "home_phlebotomy"}],
}

LABELS = {  # human-readable concept names for explanations
    "en": {"fever": "fever", "cough": "cough", "weakness": "weakness", "pain": "pain", "stomach_upset": "stomach upset",
           "bp_sugar_check": "BP/sugar check", "injection": "an injection", "dressing": "wound dressing",
           "catheter": "catheter care", "iv_drip": "an IV drip", "nebulization": "nebulization", "lab_test": "a lab test",
           "consult": "a doctor consultation", "report_review": "a report review"},
    "hi": {"fever": "बुखार", "cough": "खांसी", "weakness": "कमजोरी", "pain": "दर्द", "stomach_upset": "पेट की परेशानी",
           "bp_sugar_check": "बीपी/शुगर जांच", "injection": "इंजेक्शन", "dressing": "घाव की ड्रेसिंग",
           "catheter": "कैथेटर देखभाल", "iv_drip": "आईवी ड्रिप", "nebulization": "नेबुलाइज़ेशन", "lab_test": "लैब टेस्ट",
           "consult": "डॉक्टर से सलाह", "report_review": "रिपोर्ट की समीक्षा"},
    "hinglish": {"fever": "bukhar", "cough": "khansi", "weakness": "kamzori", "pain": "dard", "stomach_upset": "pet ki pareshani",
                 "bp_sugar_check": "BP/sugar check", "injection": "injection", "dressing": "wound dressing",
                 "catheter": "catheter care", "iv_drip": "IV drip", "nebulization": "nebulization", "lab_test": "lab test",
                 "consult": "doctor se salah", "report_review": "report review"},
}


def extract_concepts(text_norm: str) -> tuple[dict[str, FactStatus], dict[str, str]]:
    statuses: dict[str, FactStatus] = {}
    evidence: dict[str, str] = {}
    for cid, (_group, rx) in _COMPILED.items():
        matches = list(rx.finditer(text_norm))
        if not matches:
            continue
        live = [m for m in matches if not is_negated(text_norm, m.start(), m.end())]
        if live:
            statuses[cid] = FactStatus.PRESENT
            evidence[cid] = live[0].group(0)
        else:
            statuses[cid] = FactStatus.ABSENT
            evidence[cid] = matches[0].group(0)
    return statuses, evidence


def group_of(concept: str) -> str:
    return CONCEPTS[concept][0]
