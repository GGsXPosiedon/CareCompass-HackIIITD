"""Deterministic symptom pathways (NHS 111 style): cues -> <= 4 fixed questions -> fixed disposition, every outcome explained.

No model weights, no network: everything comes from app/rules/pathways.json (UNREVIEWED demo content, built by
pipeline/scripts/build_pathways.py). The LLM chat may reword questions and advice, but the disposition comes from here.
Wired into the LangGraph conversation flow; state is reconstructed from conversation history.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

RULES = Path(__file__).resolve().parents[1] / "rules" / "pathways.json"
LANGS = ("en", "hi", "hinglish")
ORDER = {"self_care": 0, "routine": 1, "urgent": 2, "emergency": 3}
URGENCY = {"emergency": "emergency", "urgent": "same_day", "routine": "scheduled", "self_care": "scheduled"}
YES_RX = re.compile(r"\b(yes|yeah|yep|haan|han|ha|haa|ji haan)\b|^(हाँ|हां|जी)|^(?:hai|ho raha hai|hota hai)$", re.I)
NO_RX = re.compile(r"\b(no|nope|nahi|nahin|nhi|na|nai)\b|^(नहीं|नही)", re.I)
UNSURE_RX = re.compile(r"(not sure|don'?t know|dont know|pata nahi|pata nhi|maloom nahi|पता नहीं|पता नही|idk)", re.I)


@lru_cache(maxsize=1)
def load() -> dict:
    from .clinical_reference import load as load_reference

    spec = json.loads(RULES.read_text(encoding="utf-8"))
    spec["pathways"].extend(load_reference()["pathways"])
    return spec


def _pw(pid: str) -> dict:
    return next(p for p in load()["pathways"] if p["id"] == pid)


def _txt(d: dict, lang: str) -> str:
    return d.get(lang) or d["en"]


def select(text: str) -> Optional[str]:
    """Pathway whose cues match the text best (most distinct cue hits); None when nothing matches."""
    from .lexicon import normalize, is_negated

    t = normalize(text)
    best, best_n = None, 0
    for p in load()["pathways"]:
        n = sum(1 for rx in p["cues"] if any(not is_negated(t, m.start(), m.end()) for m in re.finditer(rx, t, re.I)))
        if n > best_n:
            best, best_n = p["id"], n
    return best


def age_group(age_years: Optional[float]) -> Optional[str]:
    if age_years is None:
        return None
    g = load()["strictness"]["age_groups"]
    if age_years < g["infant"]["max_years"]:
        return "infant"
    if age_years < g["child"]["max_years"]:
        return "child"
    if age_years >= g["elder"]["min_years"]:
        return "elder"
    return None


def parse_answer(pid: str, qid: str, text: str, lang: str = "en") -> Optional[str]:
    """Map a free-text or tapped reply to an option id of the question; None if it cannot be understood."""
    q = next(q for q in _pw(pid)["questions"] if q["id"] == qid)
    t = " ".join(text.casefold().split())
    for o in q["options"]:
        if any(t == " ".join(o["label"][l].casefold().split()) for l in LANGS):
            return o["id"]
    ids = {o["id"] for o in q["options"]}
    if UNSURE_RX.search(t) and "unsure" in ids:
        return "unsure"
    if "yes" in ids:
        if NO_RX.search(t) and not YES_RX.search(t):
            return "no"
        if YES_RX.search(t) and not NO_RX.search(t):
            return "yes"
    return None


@dataclass
class Step:
    kind: str                                   # question | disposition
    pathway: str
    question_id: Optional[str] = None
    question: Optional[str] = None
    options: list = field(default_factory=list)   # [{id, label}]
    disposition: Optional[str] = None           # emergency | urgent | routine | self_care
    care_type: Optional[str] = None
    urgency: Optional[str] = None
    why: Optional[str] = None
    advice: Optional[str] = None
    rule: Optional[str] = None
    raised_by: Optional[str] = None             # strictness group that raised the level
    asked: int = 0
    reviewed: bool = False


def _matches(rule: dict, answers: dict) -> bool:
    return all(answers.get(q) in allowed for q, allowed in rule["when"].items())


def evaluate(pid: str, answers: dict, age_years: Optional[float] = None, pregnant: bool = False, lang: str = "en") -> Step:
    """Next step for a pathway. `answers` maps question id -> option id ('skip' = user could not answer; treated as 'unsure')."""
    p, cfg = _pw(pid), load()
    answers = {k: ("unsure" if v == "skip" else v) for k, v in answers.items()}
    qs = p["questions"][: cfg["max_questions"]]
    done = all(q["id"] in answers for q in qs)
    hit = None
    for i, r in enumerate(p["rules"]):
        final_only = r["disposition"] in ("self_care", "routine")
        if _matches(r, answers) and (done or not final_only):
            hit = (i, r)
            break
    # Unknown danger signs cannot confirm an emergency or unlock self-care.
    # A confirmed emergency rule still wins if another answer is unknown.
    unknown_danger = any(q["danger"] and answers.get(q["id"]) == "unsure" for q in qs)
    if unknown_danger and (hit is None or hit[1]["disposition"] != "emergency"):
        why = {"en": "It's okay if you're not sure. A doctor can assess this with you today. If chest pain, difficulty breathing, collapse or heavy bleeding occurs, call 112 immediately.",
               "hinglish": "Pata nahi ho to koi baat nahi. Aaj doctor aapki baat sunkar assessment kar sakte hain. Seene mein dard, saans mein taklif, behoshi ya tez khoon behna ho to turant 112 call karein.",
               "hi": "पता न हो तो कोई बात नहीं। आज डॉक्टर आपकी बात सुनकर जाँच कर सकते हैं। सीने में दर्द, साँस में तकलीफ़, बेहोशी या तेज़ खून बहने पर तुरंत 112 पर कॉल करें।"}
        return Step("disposition", pid, disposition="urgent", care_type="teleconsultation", urgency="same_day",
                    why=_txt(why, lang), rule=f"{pid}#unknown", asked=len(answers))
    if hit is None and not done:
        q = next(q for q in qs if q["id"] not in answers)
        return Step("question", pid, q["id"], _txt(q["text"], lang), [{"id": o["id"], "label": _txt(o["label"], lang)} for o in q["options"]], asked=len(answers))
    if hit is None:  # every question answered and no rule fits: conservative default
        disp, care, why, advice, rule = "urgent", "teleconsultation", {"en": "Answers do not fit a standard pattern; a doctor should look today.", "hinglish": "Jawab standard pattern mein fit nahi hue; aaj doctor dekhe.", "hi": "जवाब सामान्य पैटर्न में फिट नहीं हुए; आज डॉक्टर देखें।"}, None, "default"
    else:
        r = hit[1]
        disp, care, why, advice, rule = r["disposition"], r["care_type"], r["why"], r.get("advice"), f"{pid}#{hit[0]}"
    raised = None
    raise_map = cfg["strictness"]["raise"]
    for group in (age_group(age_years), "pregnant" if pregnant else None):
        if group and disp in raise_map.get(group, {}):
            new = raise_map[group][disp]
            if ORDER[new] > ORDER[disp]:
                disp, raised = new, group
                advice = None  # no self-care advice once raised
                if care == "teleconsultation" and disp == "urgent":
                    care = "paramedic_home_visit" if group == "infant" else care
    if disp == "emergency":
        care, advice = "emergency_112", None
    return Step("disposition", pid, disposition=disp, care_type=care, urgency=URGENCY[disp], why=_txt(why, lang) if isinstance(why, dict) else why,
                advice=_txt(advice, lang) if advice else None, rule=rule, raised_by=raised, asked=len(answers), reviewed=False)


def question_slot(text: str) -> Optional[str]:
    for p in load()["pathways"]:
        for q in p["questions"]:
            if text.strip() in q["text"].values():
                return f"pathway:{p['id']}:{q['id']}"
    return None


def conversation_step(analysis, context, mood) -> Optional[Step]:
    """Replay only the current episode; no server session or model is needed."""
    if analysis.act not in ("health", "answer") or analysis.service_request:
        return None
    messages = [*analysis.scoped_history, {"role": "user", "content": analysis.scoped_user[-1]}]
    pid, answers, pending = None, {}, None
    for turn in messages:
        text = turn["content"]
        if turn["role"] == "assistant":
            slot = question_slot(text)
            pending = slot.split(":")[1:] if slot else None
        elif pending:
            question_pid, qid = pending
            if pid != question_pid:
                pid, answers = question_pid, {}
            answer = parse_answer(pid, qid, text, analysis.language)
            if answer is not None:
                answers[qid] = answer
            pending = None
        elif pid is None:
            pid = select(text)
    # A short answer may add the first specific symptom/location to a previously vague episode.
    if pid is None:
        pid = select(" ".join(analysis.scoped_user))
    if pid is None:
        return None
    kwargs = dict(age_years=context.age_years if context else None,
                  pregnant=context.pregnant if context else False, lang=analysis.language)
    step = evaluate(pid, answers, **kwargs)
    budget = min(4, mood.max_questions or 4)
    # At the cap, unresolved answers remain uncertain, never silently negative.
    while step.kind == "question" and analysis.questions_asked >= budget:
        answers[step.question_id] = "unsure"
        step = evaluate(pid, answers, **kwargs)
    return step
