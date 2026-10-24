"""Choose the next follow-up question from the vetted bank.

Order of symptoms = order of appearance in the text; within a symptom: danger questions first, then bank order.
A question is skipped when (a) it was already asked, (b) its `resolves` concept is already known (present or absent),
or (c) it is for a symptom the user denied. Returns None when nothing relevant remains (the caller then commits
or falls back to the generic question)."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ..extraction.extractor import extract
from ..paths import load_yaml


@dataclass(frozen=True)
class Question:
    id: str
    symptom: str
    text: str
    options: list[str]
    danger: bool
    purpose: str


@lru_cache(maxsize=1)
def bank() -> dict:
    return load_yaml("question_bank.yaml")


def known_concepts(texts: list[str]) -> dict[str, str]:
    """concept id (no cc: prefix) -> latest assertion over all user turns."""
    known: dict[str, str] = {}
    for turn, t in enumerate(texts):
        for f in extract(t, turn).facts:
            known[f.concept_id[3:]] = f.assertion.value
    return known


def next_question(user_texts: list[str], asked_ids: list[str], language: str = "en") -> Question | None:
    b = bank()
    lang = language if language in b["options"] else "en"
    known = known_concepts(user_texts)
    present = [c for c in known if known[c] == "present" and c in b["symptoms"]]
    # preserve order of first appearance in the earliest turn that mentions each symptom
    order = {}
    for turn, t in enumerate(user_texts):
        for f in extract(t, turn).facts:
            cid = f.concept_id[3:]
            order.setdefault(cid, (turn, f.text_span[0] if f.text_span else 0))
    present.sort(key=lambda c: order.get(c, (99, 0)))
    cands = []
    for sym in present:
        for q in b["symptoms"][sym]:
            if q["id"] in asked_ids or (q.get("resolves") and q["resolves"] in known):
                continue
            cands.append((sym, q))
    cands.sort(key=lambda sq: not sq[1].get("danger", False))  # stable: all danger questions first, then symptom/bank order
    if not cands:
        return None
    sym, q = cands[0]
    return Question(q["id"], sym, q[lang], b["options"][lang], bool(q.get("danger")), q["purpose"])
