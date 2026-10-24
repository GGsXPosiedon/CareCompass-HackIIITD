"""Rule-based, multilingual (English / Hindi / Hinglish) fact extractor.

Scope: it reports what the text says. It never decides care type or urgency, and "no match" is never
evidence of absence: text with no recognised clinical concept sets `needs_clarification`.
Heuristics are documented inline; every one is covered by tests or the adversarial evaluation set.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field

from ..schemas import Assertion, Duration, Fact, Origin, Temporality
from .registry import Registry, load_registry, norm_token, tokenize

NEG_BEFORE = frozenset(norm_token(w) for w in [
    "no", "not", "without", "denies", "denied", "never", "nil", "bina", "बिना",
    "don't", "doesn't", "didn't", "haven't", "hasn't", "isn't", "wasn't", "aren't", "negative"])
NEG_AFTER = frozenset(norm_token(w) for w in ["nahi", "nahin", "nhi", "nai", "नहीं", "नही"])
# "khansi nahi ruk rahi" = the cough is NOT stopping (present). A Hindi negation followed by one of these
# verb stems is therefore not treated as negating the symptom before it.
PERSIST = frozenset(norm_token(w) for w in ["ruk", "rukna", "utar", "ruk", "रुक", "उतर", "उतर"])
CLAUSE_BREAK_WORDS = frozenset(norm_token(w) for w in [
    "but", "however", "though", "although", "while", "lekin", "par", "magar", "parantu", "लेकिन", "पर", "मगर", "परंतु"])
HYPO = frozenset(norm_token(w) for w in ["if", "agar", "yadi", "अगर", "यदि"])
PAST = frozenset(norm_token(w) for w in [
    "history", "previously", "earlier", "pehle", "पहले", "tha", "thi", "था", "थी", "थे", "recovered"])
PAST_PAIRS = (("last", "year"), ("last", "month"), ("used", "to"), ("in", "the", "past"), ("years", "ago"),
              ("months", "ago"), ("saal", "pehle"), ("साल", "पहले"))
SEVERE = frozenset(norm_token(w) for w in ["severe", "tez", "तेज", "bahut", "बहुत", "extreme", "intense"])
NUMBER_WORDS = {w: n for words, n in [
    (("one", "ek", "एक"), 1), (("two", "do", "दो"), 2), (("three", "teen", "तीन"), 3),
    (("four", "char", "चार"), 4), (("five", "paanch", "panch", "पांच"), 5), (("six", "chhe", "छह"), 6),
    (("seven", "saat", "सात"), 7), (("ten", "das", "दस"), 10)] for w in words}
UNITS = {"day": 1, "days": 1, "din": 1, "दिन": 1, "week": 7, "weeks": 7, "hafta": 7, "hafte": 7, "हफ्ते": 7,
         "हफ्ता": 7, "month": 30, "months": 30, "mahina": 30, "mahine": 30, "महीने": 30,
         "hour": 0, "hours": 0, "ghanta": 0, "ghante": 0, "घंटे": 0}
SINCE_WORDS = {"morning": ("since_morning", 0), "subah": ("since_morning", 0), "सुबह": ("since_morning", 0),
               "yesterday": ("since_yesterday", 1), "kal": ("since_yesterday", 1), "कल": ("since_yesterday", 1)}
SINCE_PRECEDES = frozenset({"since"})
SINCE_FOLLOWS = frozenset(norm_token(w) for w in ["se", "से"])


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facts: list[Fact] = Field(default_factory=list)
    experiencer: str = "unspecified"
    duration: Duration | None = None
    needs_clarification: bool = True
    ambiguity_notes: list[str] = Field(default_factory=list)


@dataclass
class _Mention:
    concept: str
    start: int  # token index
    end: int  # exclusive
    char_span: tuple[int, int]


@lru_cache(maxsize=1)
def _registry() -> Registry:
    return load_registry()


def _match_concepts(toks: list[str], reg: Registry) -> list[_Mention]:
    mentions: list[_Mention] = []
    i = 0
    while i < len(toks):
        hit = None
        for seq, cid in reg.by_first_token.get(toks[i], ()):  # longest first
            if tuple(toks[i:i + len(seq)]) == seq:
                hit = (seq, cid)
                break
        if hit:
            mentions.append(_Mention(hit[1], i, i + len(hit[0]), (0, 0)))
            i += len(hit[0])
        else:
            i += 1
    return mentions


def _clause_ids(text: str, spans: list[tuple[str, int, int]]) -> list[int]:
    ids, cur = [], 0
    for k, (tok, start, _) in enumerate(spans):
        if k and re.search(r"[,.;!?।\n]", text[spans[k - 1][2]:start]):
            cur += 1
        elif tok in CLAUSE_BREAK_WORDS:
            cur += 1
        ids.append(cur)
    return ids


def _experiencer(toks: list[str], reg: Registry, notes: list[str]) -> str:
    rels = []
    for t in toks:
        r = reg.relations.get(t)
        if r and r not in rels:
            rels.append(r)
    if len(rels) > 1:
        notes.append("multiple_people_mentioned")
        return "multiple"
    if rels:
        return rels[0]
    if any(t in reg.third_person for t in toks):
        return "other_unspecified"
    if any(t in reg.first_person for t in toks):
        return "self"
    return "unspecified"


def _duration(toks: list[str]) -> Duration | None:
    for k, t in enumerate(toks):
        n = int(t) if t.isdigit() else NUMBER_WORDS.get(t)
        if n is not None and k + 1 < len(toks) and toks[k + 1] in UNITS:
            prev = toks[k - 1] if k else ""
            nxt = toks[k + 2] if k + 2 < len(toks) else ""
            if prev in {"for", "last", "past", "since", "pichhle", "pichle"} or nxt in SINCE_FOLLOWS:
                unit = toks[k + 1]
                days = n * UNITS[unit]
                return Duration(days=days, bucket=f"{n}_{unit}")
    for k, t in enumerate(toks):
        if t in SINCE_WORDS:
            before = toks[k - 1] if k else ""
            after = toks[k + 1] if k + 1 < len(toks) else ""
            if before in SINCE_PRECEDES or after in SINCE_FOLLOWS:
                bucket, days = SINCE_WORDS[t]
                return Duration(days=days, bucket=bucket)
    return None


def _has_pair(window: list[str], pairs) -> bool:
    for p in pairs:
        for k in range(len(window) - len(p) + 1):
            if tuple(window[k:k + len(p)]) == p:
                return True
    return False


def extract(text: str, turn: int = 0, registry: Registry | None = None) -> ExtractionResult:
    reg = registry or _registry()
    spans = tokenize(text or "")
    toks = [t for t, _, _ in spans]
    notes: list[str] = []
    result = ExtractionResult(experiencer=_experiencer(toks, reg, notes), duration=_duration(toks))
    if not toks:
        result.ambiguity_notes = ["empty_text"]
        return result

    clause = _clause_ids(text, spans)
    mentions = _match_concepts(toks, reg)
    consumed = {k for m in mentions for k in range(m.start, m.end)}

    per_concept: dict[str, list[tuple[Assertion, Temporality, str | None, tuple[int, int]]]] = {}
    for m in mentions:
        c = clause[m.start]
        same = [k for k in range(len(toks)) if clause[k] == c]
        before = [k for k in same if k < m.start and k not in consumed]
        # Negation: an English cue up to 5 tokens before (list scope: "no fever or cough") ...
        negated = any(toks[k] in NEG_BEFORE and m.start - k <= 5 for k in before)
        # ... or a Hindi cue up to 2 tokens after, unless it is "nahi ruk" style (symptom persists).
        if not negated:
            for k in range(m.end, min(m.end + 2, len(toks))):
                if k in consumed or clause[k] != c:
                    continue
                if toks[k] in NEG_AFTER:
                    follow = toks[k + 1:k + 3]
                    if not any(f in PERSIST for f in follow):
                        negated = True
                    break
        clause_toks = [toks[k] for k in same]
        hypothetical = any(toks[k] in HYPO for k in before)
        past = any(toks[k] in PAST for k in same if k not in consumed) or _has_pair(clause_toks, PAST_PAIRS)
        if negated:
            assertion, temporality = Assertion.ABSENT, Temporality.UNSPECIFIED
        elif hypothetical:
            assertion, temporality = Assertion.HYPOTHETICAL, Temporality.UNSPECIFIED
        elif past:
            assertion, temporality = Assertion.HISTORICAL, Temporality.PAST
        else:
            assertion, temporality = Assertion.PRESENT, Temporality.CURRENT
        severity = "severe" if any(toks[k] in SEVERE for k in range(max(0, m.start - 2), m.start)) else None
        span = (spans[m.start][1], spans[m.end - 1][2])
        per_concept.setdefault(m.concept, []).append((assertion, temporality, severity, span))

    for cid, items in per_concept.items():
        kinds = {a for a, _, _, _ in items}
        if Assertion.PRESENT in kinds and Assertion.ABSENT in kinds:
            final = Assertion.CONFLICTING
            notes.append(f"conflicting_mentions:{cid}")
        else:
            for candidate in (Assertion.PRESENT, Assertion.ABSENT, Assertion.HISTORICAL, Assertion.HYPOTHETICAL):
                if candidate in kinds:
                    final = candidate
                    break
        chosen = next(it for it in items if it[0] is final or final is Assertion.CONFLICTING)
        temporality = {Assertion.PRESENT: Temporality.CURRENT, Assertion.HISTORICAL: Temporality.PAST}.get(
            final, Temporality.UNSPECIFIED)
        result.facts.append(Fact(
            concept_id=f"cc:{cid}", assertion=final, value=True if final is Assertion.PRESENT else None,
            value_label=chosen[2], temporality=temporality, evidence_turn=turn, text_span=chosen[3],
            origin=Origin.EXTRACTED_RULE, experiencer=result.experiencer))

    result.needs_clarification = not any(
        f.assertion in (Assertion.PRESENT, Assertion.CONFLICTING) and not reg.concepts[f.concept_id[3:]].generic
        for f in result.facts)
    result.ambiguity_notes = notes
    return result
