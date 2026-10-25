"""Small, offline navigation reference curated from the supplied STW manual.

Only source-authored paraphrases live here: user text and the original PDF cannot supply instructions.
This is reference retrieval, not diagnosis or an alternative safety engine.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

REFERENCE = Path(__file__).resolve().parents[1] / "rules/stw_reference.json"


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(REFERENCE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _topics() -> list:
    from .lexicon import normalize

    return [(t, re.compile(r"(?<!\w)(?:" + "|".join(re.escape(normalize(a)) for a in t["aliases"]) + r")(?!\w)")) for t in load()["topics"]]


def related(text: str, limit: int = 3) -> list[dict]:
    from .lexicon import is_negated, normalize

    from .dialogue import _n

    normal = _n(text)
    normal = re.sub(r"\bno (\w+) or (\w+)\b", r"no \1 no \2", normal)
    text = normal
    pages = {page for p in load()["pathways"] if any(
        not is_negated(normal, m.start(), m.end()) for cue in p["cues"] for m in re.finditer(cue, normal, re.I)) for page in p["source_pages"]}
    hits = [(10 * sum(1 for m in rx.finditer(text) if not is_negated(text, m.start(), m.end())) + int(t["pdf_page"] in pages), t) for t, rx in _topics()]
    return [t for count, t in sorted(hits, key=lambda pair: -pair[0]) if count][:limit]


def context(text: str) -> str:
    topics = related(text)
    if not topics:
        return ""
    excerpts = [dict(topic=t["title"], source=f"ICMR_STW_2019_V1 PDF page {t['pdf_page']}",
                     intake=t["intake"], warning_signs=t["warning_signs"], navigation=t["navigation"]) for t in topics]
    from .lexicon import normalize

    normal = normalize(text)
    ids = {p["id"] for p in load()["pathways"] if any(re.search(cue, normal, re.I) for cue in p["cues"])}
    examples = [e for e in load()["examples"] if e["expect"] in ids][:2]
    return ("\n<clinical_reference>\nUNREVIEWED navigation adaptation of a clinician manual. Related topics are NOT patient diagnoses. "
            "Use only to choose relevant questions and referral context. Confirm facts from the user's words; never infer absent details. "
            "Do not prescribe, diagnose, calculate clinical scores or claim a referral/visit is booked.\n"
            + json.dumps(dict(topics=excerpts, synthetic_navigation_examples=examples), ensure_ascii=False) + "\n</clinical_reference>")


def extract_details(text: str) -> dict:
    """Capture only explicitly stated facts; a test/condition mention never becomes a clinical result."""
    from .lexicon import extract_concepts, normalize

    statuses, evidence = extract_concepts(normalize(text))
    age = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*(years?(?: old)?|yrs?|saal|months?(?: old)?|mahine|weeks?(?: old)?|hafte|साल|महीने|सप्ताह)\b", re.I)
    measurements = {
        "temperature": r"(?<!\d)(?:3[5-9]|4[0-2]|9[5-9]|10[0-9])(?:\.\d+)?\s*(?:°\s*)?(?:celsius|fahrenheit|degrees?\s*[cf]|[cf])\b",
        "blood_pressure": r"\b(?:bp|blood pressure|बीपी)\s*(?:is|hai|है|:)?\s*\d{2,3}\s*/\s*\d{2,3}\b",
        "oxygen_saturation": r"\b(?:spo2|oxygen saturation|ऑक्सीजन)\s*(?:is|hai|है|:)?\s*\d{2,3}\s*%?",
        "pulse": r"\b(?:pulse|heart rate|नाड़ी)\s*(?:is|hai|है|:)?\s*\d{2,3}\s*(?:bpm|/min)?",
    }
    return dict(symptoms={key: dict(status=status.value, evidence=evidence[key]) for key, status in statuses.items()
                          if key in load()["symptom_concepts"] or key in ("fever", "cough", "pain", "weakness", "stomach_upset")},
                stated_ages=[dict(value=float(m.group(1)), unit=m.group(2).casefold(), evidence=m.group(0)) for m in age.finditer(text)
                             if re.search(r"(?:age|aged|umar|umr|उम्र)\s*(?:is|hai|है|:)?\s*$", text[max(0, m.start()-20):m.start()], re.I)
                             or "old" in m.group(2).casefold() or re.match(r"\s*(?:ka|ki|के|का|की)\b", text[m.end():], re.I)],
                measurements={key: [m.group(0) for m in re.finditer(pattern, text, re.I)] for key, pattern in measurements.items()
                              if re.search(pattern, text, re.I)},
                related_reference_topics=[dict(id=t["id"], pdf_page=t["pdf_page"]) for t in related(text)])


def acknowledgement(language: str, *, unknown: bool = False, continuing: bool = False) -> str:
    if unknown:
        return {"en": "That's okay if you're not sure. We'll work with what you can tell us.",
                "hinglish": "Pata nahi ho to koi baat nahi. Jo aap bata sakein, usse agla kadam samajhte hain.",
                "hi": "पता न हो तो कोई बात नहीं। आप जो बता सकें, उससे अगला कदम समझते हैं।"}[language]
    if continuing:
        return {"en": "Thanks for telling me. Just one more detail.",
                "hinglish": "Batane ke liye shukriya. Bas ek aur baat samajhni hai.",
                "hi": "बताने के लिए धन्यवाद। बस एक और बात समझनी है।"}[language]
    return {"en": "Let's take this one step at a time. A short answer is fine.",
            "hinglish": "Ek-ek karke samajhte hain. Chhota sa jawab bhi chalega.",
            "hi": "एक-एक करके समझते हैं। छोटा सा जवाब भी चलेगा।"}[language]
