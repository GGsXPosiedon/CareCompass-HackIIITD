"""Deterministic mood cues (panic / anger / anxiety) in English, Hindi and Hinglish, and how each should change the conversation.

Rules, not a model. The LLM writes the wording; this module decides the stance and routing flags:
  panic   -> ask the danger-sign question first, treat 'unsure' as yes, short calm sentences, offer 112
  anger   -> apologise once, no more than one question, offer a human call-back
  anxiety -> reassure and explain the next step; same disposition as for a calm user (never lowers urgency)
Mood can only add caution or a human hand-off. It never downgrades a disposition.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PANIC = re.compile(r"(please (?:help|hurry)|help me|jaldi (?:karo|aao|bhejo)|bachao|bacha lo|koi to|pls pls|urgent urgent|dying|\bmar (?:raha|rahi|jayega|jayegi)|मर रहा|मर रही|बचाओ|जल्दी (?:करो|आओ|भेजो)|मदद करो|ghabra gaya|ghabra gayi|घबरा|panic|oh god|हे भगवान|emergency emergency|!!!)", re.I)
ANGER = re.compile(r"(useless|waste of time|bakwas|bekaar|bekar|faltu|stupid|idiot|worst|nonsense|kuch kaam ka nahi|sab bekaar|gussa|gussa aa|pagal|बकवास|बेकार|फालतू|घटिया|गुस्सा|कोई फायदा नहीं|fed up|sick of this|why (?:are you|is this) so)", re.I)
ANXIETY = re.compile(r"(worried|worry|scared|afraid|anxious|nervous|tension|tensed|dar lag|darr|chinta|fikar|ghabrahat|ghabrah|डर|चिंता|फिक्र|घबराहट|टेंशन|what if|kya hoga|serious (?:to )?nahi|is it serious)", re.I)


@dataclass(frozen=True)
class Mood:
    label: str                 # panic | anger | anxiety | neutral
    danger_first: bool = False
    unsure_is_yes: bool = False
    max_questions: int | None = None
    human_callback: bool = False
    tone: str = "neutral"
    cues: tuple = ()


def detect(text: str) -> Mood:
    t = text.casefold()
    p, a, x = (rx.findall(t) for rx in (PANIC, ANGER, ANXIETY))
    if p or text.count("!") >= 3:
        return Mood("panic", danger_first=True, unsure_is_yes=True, tone="calm, short sentences, say 112 is available", cues=tuple(map(str, p)) or ("!!!",))
    if a:
        return Mood("anger", max_questions=1, human_callback=True, tone="apologise once, be brief, offer a human call-back", cues=tuple(map(str, a)))
    if x:
        return Mood("anxiety", tone="reassure, explain the next step, keep the disposition unchanged", cues=tuple(map(str, x)))
    return Mood("neutral")
