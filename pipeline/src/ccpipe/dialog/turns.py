"""Turn-type classification (rule baseline). Flags are not exclusive; `primary` is chosen by a fixed safety order.

crisis > symptom > decline > abuse > distress > greeting > answer > no_health
This is the swap-in point for a learned intent/emotion model: same input, same TurnInfo output."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from ..extraction.extractor import extract
from ..paths import load_yaml

_RUNS = re.compile(r"(.)\1{2,}")
_ER_SIGNS = {"collapse", "unresponsive", "bleeding_heavy", "chest_pain", "breathlessness"}
_HINGLISH = set("hai hain mujhe mere meri nahi nhi kya ko se ka ki mai main hoon hu din bukhar dard kab kal aaj thoda bahut "
                "chahiye chaiye theek thik haan han ho raha rahi rahe lag raha aur bhi jaa ja".split())


@lru_cache(maxsize=1)
def cfg() -> dict:
    c = load_yaml("dialog.yaml")
    c["_re"] = {k: [re.compile(p) for p in v] for k, v in c["patterns"].items()}
    return c


def collapse(text: str) -> str:
    return _RUNS.sub(r"\1", text.lower().strip())


def detect_language(text: str) -> str:
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    words = set(re.findall(r"[a-z']+", collapse(text)))
    return "hinglish" if len(words & _HINGLISH) >= 1 else "en"


def _hit(kind: str, text: str) -> bool:
    return any(p.search(text) for p in cfg()["_re"][kind])


@dataclass
class TurnInfo:
    primary: str
    flags: set[str] = field(default_factory=set)
    symptoms: list[str] = field(default_factory=list)
    language: str = "en"


def classify(text: str, awaiting_answer: bool = False) -> TurnInfo:
    t = collapse(text)
    res = extract(text)
    present = [f.concept_id[3:] for f in res.facts if f.assertion.value == "present"]
    symptoms = [c for c in present if c in cfg()["names"]]
    flags = {k for k in ("crisis", "decline", "abuse", "distress", "greeting") if _hit(k, t)}
    if symptoms:
        flags.add("symptom")
    if _ER_SIGNS & set(present):
        flags.add("emergency_sign")
    for primary in ("crisis", "symptom", "decline", "abuse", "distress", "greeting"):
        if primary in flags:
            break
    else:
        primary = "answer" if awaiting_answer else "no_health"
    return TurnInfo(primary, flags, symptoms, detect_language(text))
