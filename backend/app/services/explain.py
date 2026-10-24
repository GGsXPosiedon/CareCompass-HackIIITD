"""Module F: explanations built from structured facts only (never from free text or an LLM)."""
from __future__ import annotations

from ..config import EMERGENCY_NUMBER, MENTAL_HEALTH_HELPLINE
from ..schemas.internal import CaseFacts, RouteDecision, SafetyResult
from .lexicon import LABELS

FLAG_NAMES = {
    "en": {"chest_pain": "chest pain", "breathlessness": "difficulty breathing", "unconsciousness": "loss of consciousness",
           "severe_bleeding": "severe bleeding", "stroke_symptoms": "possible stroke signs", "seizure": "seizure",
           "high_fever_infant": "high fever in an infant", "suicidal_ideation": "thoughts of self-harm",
           "severe_dehydration": "severe dehydration"},
    "hi": {"chest_pain": "सीने में दर्द", "breathlessness": "सांस लेने में तकलीफ", "unconsciousness": "बेहोशी",
           "severe_bleeding": "ज्यादा खून बहना", "stroke_symptoms": "स्ट्रोक के संभावित लक्षण", "seizure": "दौरा/मिर्गी",
           "high_fever_infant": "शिशु में तेज बुखार", "suicidal_ideation": "खुद को नुकसान के विचार",
           "severe_dehydration": "गंभीर डिहाइड्रेशन"},
    "hinglish": {"chest_pain": "seene mein dard", "breathlessness": "saans lene mein taklif", "unconsciousness": "behoshi",
                 "severe_bleeding": "bahut khoon behna", "stroke_symptoms": "stroke ke sanket", "seizure": "daura/mirgi",
                 "high_fever_infant": "shishu mein tez bukhar", "suicidal_ideation": "khud ko nuksan ke vichar",
                 "severe_dehydration": "gambhir dehydration"},
}


def emergency_text(safety: SafetyResult, language: str) -> str:
    names = ", ".join(FLAG_NAMES[language][f] for f in safety.flags) or {"en": "serious symptoms", "hi": "गंभीर लक्षण", "hinglish": "gambhir lakshan"}[language]
    n = EMERGENCY_NUMBER
    if language == "hi":
        text = (f"यह आपात स्थिति हो सकती है ({names})। अभी {n} पर कॉल करें। घर पर किसी के आने का इंतज़ार न करें। "
                "मरीज़ के साथ रहें, उन्हें शांत रखें और एम्बुलेंस के लिए दरवाज़ा खुला रखें।")
        if "suicidal_ideation" in safety.flags:
            text += f" उन्हें अकेला न छोड़ें। मानसिक स्वास्थ्य सहायता: {MENTAL_HEALTH_HELPLINE}।"
    elif language == "hinglish":
        text = (f"Yeh emergency ho sakti hai ({names}). Abhi {n} par call karein. Ghar par kisi ke aane ka intezaar na karein. "
                "Patient ke saath rahein, unhe shant rakhein aur ambulance ke liye darwaza khula rakhein.")
        if "suicidal_ideation" in safety.flags:
            text += f" Unhe akela na chhodein. Mental health helpline: {MENTAL_HEALTH_HELPLINE}."
    else:
        text = (f"This may be an emergency ({names}). Call {n} now. Do not wait for a home visit. "
                "Stay with the patient, keep them calm and still, and unlock the door for the ambulance.")
        if "suicidal_ideation" in safety.flags:
            text += f" Do not leave them alone. Mental health helpline: {MENTAL_HEALTH_HELPLINE}."
    if safety.source == "model_guard":
        text += {"en": " (Escalated as a precaution.)", "hi": " (एहतियात के तौर पर बढ़ाया गया।)", "hinglish": " (Ehtiyat ke taur par escalate kiya gaya.)"}[language]
    return text


_BASE = {
    "en": {
        "paramedic_home_visit": "A Medic can assess this at home{ev}. If breathing trouble, chest pain or confusion starts, call 112.",
        "home_nursing": "This needs a nursing procedure at home{ev}. A Medic will visit.",
        "lab_test_home": "A home sample collection is the right service{ev}.",
        "teleconsultation": "This looks suitable for a video/phone consultation with a doctor{ev}.",
    },
    "hi": {
        "paramedic_home_visit": "मेडिक घर पर जांच कर सकते हैं{ev}। सांस लेने में तकलीफ, सीने में दर्द या भ्रम हो तो 112 पर कॉल करें।",
        "home_nursing": "इसके लिए घर पर नर्सिंग सेवा चाहिए{ev}। एक मेडिक आएंगे।",
        "lab_test_home": "घर से सैंपल कलेक्शन सही सेवा है{ev}।",
        "teleconsultation": "यह डॉक्टर से वीडियो/फोन परामर्श के लिए उपयुक्त लगता है{ev}।",
    },
    "hinglish": {
        "paramedic_home_visit": "Medic ghar pe check kar sakte hain{ev}. Saans mein taklif, seene mein dard ya confusion ho to 112 par call karein.",
        "home_nursing": "Isme ghar par nursing procedure chahiye{ev}. Ek Medic aayenge.",
        "lab_test_home": "Ghar se sample collection sahi service hai{ev}.",
        "teleconsultation": "Yeh doctor ke saath video/phone consult ke liye theek lagta hai{ev}.",
    },
}
_STATED = {"en": " (you mentioned: {t})", "hi": " (आपने बताया: {t})", "hinglish": " (aapne bataya: {t})"}
_FALLBACK = {
    "en": " Not enough detail was given, so a Medic assessment is the safest default.",
    "hi": " पर्याप्त जानकारी नहीं मिली, इसलिए मेडिक जांच सबसे सुरक्षित विकल्प है।",
    "hinglish": " Poori jaankari nahi mili, isliye Medic assessment sabse safe default hai.",
}
_NONE = {
    "en": " No eligible caregiver is available right now.",
    "hi": " अभी कोई उपयुक्त देखभालकर्ता उपलब्ध नहीं है।",
    "hinglish": " Abhi koi eligible caregiver available nahi hai.",
}


# Symptom-specific "when to call 112" lines and warning signs the user may have confirmed. DRAFT wording written by the
# dev team, NOT clinician-reviewed. Used only for explanation text; they never change care type, urgency or red flags.
import re as _re

DANGER_LINE = {
    "headache": {
        "en": "If the headache is sudden or the worst you have had, or comes with trouble speaking, weakness, repeated vomiting or fainting, call 112.",
        "hi": "अगर सिरदर्द अचानक या सबसे तेज़ हो, या बोलने में दिक्कत, कमज़ोरी, बार-बार उल्टी या बेहोशी हो तो 112 पर कॉल करें।",
        "hinglish": "Agar sir dard achanak ya sabse tez ho, ya bolne mein dikkat, kamzori, baar-baar ulti ya behoshi ho to 112 par call karein."},
    "knee_pain": {
        "en": "If the knee is hot and very swollen with fever, or you cannot put weight on it after a fall, get urgent care or call 112.",
        "hi": "अगर घुटना गर्म और बहुत सूजा हो और बुखार हो, या गिरने के बाद वज़न न डाल पाएं तो तुरंत इलाज लें या 112 पर कॉल करें।",
        "hinglish": "Agar ghutna garam aur bahut sujha ho aur bukhar ho, ya girne ke baad wazan na daal paayein to turant care lein ya 112 par call karein."},
    "stomach_pain": {
        "en": "If the pain is severe, there is blood in vomit or stool, or the belly is hard, call 112 or go to the nearest emergency department.",
        "hi": "अगर दर्द बहुत तेज़ हो, उल्टी या मल में खून हो, या पेट सख्त हो तो 112 पर कॉल करें।",
        "hinglish": "Agar dard bahut tez ho, ulti ya potty mein khoon ho, ya pet sakht ho to 112 par call karein."},
}
ASSOC = [  # (regex over the user's words, label per language, is_warning_sign)
    (_re.compile(r"dhundh?la|blurr?y|blurred|धुंधला"), {"en": "blurred vision", "hi": "धुंधला दिखना", "hinglish": "dhundhla dikhna"}, True),
    (_re.compile(r"\bulti\b|vomit|उल्टी"), {"en": "vomiting", "hi": "उल्टी", "hinglish": "ulti"}, False),
    (_re.compile(r"\bbukhar\b|\bfever\b|बुखार"), {"en": "fever", "hi": "बुखार", "hinglish": "bukhar"}, False),
    (_re.compile(r"sujan|swell|सूजन"), {"en": "swelling", "hi": "सूजन", "hinglish": "sujan"}, False),
    (_re.compile(r"sunn|numb|सुन्न"), {"en": "numbness", "hi": "सुन्नपन", "hinglish": "sunnpan"}, True),
]
_WARN_TAIL = {"en": " {x} together with {s} can be a warning sign: if it gets worse, call 112.",
              "hi": " {s} के साथ {x} चेतावनी का संकेत हो सकता है: बढ़े तो 112 पर कॉल करें।",
              "hinglish": " {s} ke saath {x} warning sign ho sakta hai: badhe to 112 par call karein."}


def dialogue_name(key: str, lang: str) -> str:
    from . import dialogue

    return dialogue.NAMES[key][lang]


def _symptom_summary(facts: CaseFacts) -> tuple[list[str], list[str], str | None]:
    """(symptom/concept names, confirmed associated names, main symptom key) from the dialogue analysis."""
    a = getattr(facts, "analysis", None)
    if a is None:
        return [], [], None
    from . import dialogue

    lang = facts.language
    names = [dialogue.NAMES[k][lang] if k in dialogue.NAMES else dialogue._symptom_text(k, lang) for k in a.symptoms if k in dialogue.NAMES or k.startswith("other:")]
    text = " ".join(a.scoped_user).lower()
    assoc, warn = [], []
    for rx, label, is_warn in ASSOC:
        if rx.search(text) and label[lang] not in names:
            assoc.append(label[lang])
            if is_warn:
                warn.append(label[lang])
    return names, assoc + [], (a.symptoms[0] if a.symptoms else None) if not warn else (a.symptoms[0] if a.symptoms else None)


def decision_text(facts: CaseFacts, decision: RouteDecision, care_type: str, *, fallback: bool, no_match: bool) -> str:
    lang = facts.language
    labels = LABELS[lang]
    mentioned = [labels[c] for c in decision.evidence if c in labels]
    names, assoc, main = _symptom_summary(facts)
    shown = list(dict.fromkeys([*names, *[m for m in mentioned if m not in names and not (names and m == labels.get("pain"))], *assoc]))
    ev = _STATED[lang].format(t=", ".join(shown)) if shown else ""
    text = _BASE[lang][care_type].format(ev=ev)
    if care_type == "paramedic_home_visit" and main in DANGER_LINE:  # symptom-specific safety line instead of the generic one
        generic = _BASE[lang][care_type].format(ev="")
        cut = generic.rfind(". ") if lang != "hi" else generic.rfind("। ")
        text = _BASE[lang][care_type].format(ev=ev)[: len(text) - (len(generic) - cut - 2)] + DANGER_LINE[main][lang] if cut > 0 else text
        for rx, label, is_warn in ASSOC:
            if is_warn and label[lang] in assoc and main == "headache":
                nm = dialogue_name(main, lang)
                text += _WARN_TAIL[lang].format(x=label[lang], s=nm).strip().replace(nm, nm[:1].upper() + nm[1:], 1).join([" ", ""]) if lang != "hi" else _WARN_TAIL[lang].format(x=label[lang], s=nm)
    if fallback:
        text += _FALLBACK[lang]
    if no_match:
        text += _NONE[lang]
    return text


def no_match_suffix(language: str) -> str:
    return _NONE[language]
