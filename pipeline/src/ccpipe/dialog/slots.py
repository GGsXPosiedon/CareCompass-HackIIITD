"""Clinical slots: parse values from replies, render slot questions, recognise our own questions in the history."""
from __future__ import annotations

import re
from functools import lru_cache

from ..extraction.extractor import extract
from .turns import cfg, collapse, _hit

TEMP_F = re.compile(r"\b(9[4-9]|10[0-9]|11[0-1])(\.\d)?\b")
TEMP_C = re.compile(r"\b(3[5-9]|4[0-2])(\.\d)?\s*(°|degree|deg|c\b|celsius)")
SEV_WORDS = re.compile(r"\b(mild|moderate|severe|halka|halki|madhyam|tez|bahut|zyada|unbearable|\d{1,2}\s*(?:/|out of)\s*10)\b|तेज़|तेज|हल्का|बहुत")
AGE = re.compile(r"\b(\d{1,3})\s*(years?|yrs?|saal|sal|months?|mahine|महीने|साल|वर्ष)\b|\b(baby|infant|child|bachha|bacha|beta|beti|बच्चा)\b")

SLOTS = ("duration", "temperature", "severity_pain", "severity", "associated", "patient")


def render(slot: str, symptom: str, lang: str) -> tuple[str, list[str] | None]:
    c = cfg()
    q = c["questions"][slot]
    hints = c["hints"].get(symptom, c["hints"]["default"])[lang]
    name = c["names"].get(symptom, {"en": symptom, "hi": symptom, "hinglish": symptom})[lang]
    return q[lang].format(symptom=name, hints=hints), (q.get("options") or {}).get(lang)


@lru_cache(maxsize=1)
def _recognisers() -> list[tuple[str, re.Pattern]]:
    out = []
    for slot, q in cfg()["questions"].items():
        for lang in ("en", "hi", "hinglish"):
            pat = re.escape(q[lang]).replace(re.escape("{symptom}"), ".+").replace(re.escape("{hints}"), ".+")
            out.append((slot, re.compile("^" + pat + "$")))
    return out


def slot_of_assistant(text: str) -> str | None:
    for slot, rx in _recognisers():
        if rx.match(text.strip()):
            return slot
    return None


def filled_from_text(text: str, pending: str | None) -> dict[str, object]:
    """Slot values this user message supplies. `pending` is the slot the previous assistant turn asked."""
    t = collapse(text)
    out: dict[str, object] = {}
    d = extract(text).duration
    if d is not None and (d.days is not None or d.bucket):
        out["duration"] = d.days if d.days is not None else d.bucket
    m = TEMP_F.search(t) or TEMP_C.search(t)
    if m:
        out["temperature"] = m.group(0)
    if SEV_WORDS.search(t):
        out["severity"] = out["severity_pain"] = SEV_WORDS.search(t).group(0)
    if re.search(r"\b\d{1,2}\b", t) and pending == "severity_pain":
        out["severity_pain"] = re.search(r"\b\d{1,2}\b", t).group(0)
    if AGE.search(t) or extract(text).experiencer not in ("unspecified", "self"):
        out["patient"] = True
    if pending and _hit("unsure", t):
        out[pending] = "unknown"
    if pending == "associated":
        out["associated"] = True if (_hit("yes_ans", t) or _hit("no_ans", t) or extract(text).facts) else out.get("associated")
    if pending == "temperature" and _hit("no_ans", t):
        out["temperature"] = "not_measured"
    if pending == "duration" and "duration" not in out and re.search(r"\b(aaj|today|abhi|just now|subah|morning|raat)\b|आज|अभी", t):
        out["duration"] = "today"
    return {k: v for k, v in out.items() if v is not None}
