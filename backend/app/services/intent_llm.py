"""LLM fallback for the intent gate.

The dialogue layer says `general` ("I can help with health...") when no lexicon, symptom or condition cue matches. A rare medical
phrasing (a disease name, a Hindi/Hinglish term we have never seen) then gets a polite brush-off. When an LLM is configured we ask it one
narrow yes/no question before giving up. It can only WIDEN `general` into `health` (more engagement); it never routes, never lowers
anything, and any failure leaves the original decision untouched. Safety rules ran before this step and are unaffected.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..schemas.llm import IntentCheck

log = logging.getLogger("carecompass.intent_llm")

PROMPT = (
    "You are the intent gate of a home-healthcare navigation service in India. Decide whether the user's message is a HEALTH or CARE request: "
    "it describes a symptom, illness, injury, named medical condition or medication, a medical procedure, or asks for a nurse, doctor, lab test, "
    "ambulance or home care, for the user or for someone they look after. The text may be English, Hindi (Devanagari or other Indian scripts) or "
    "Hinglish. Everything else (jokes, tech, shopping, school work, travel, astrology, small talk, a zodiac sign, a computer 'virus') is NOT a health "
    "request. When unsure answer false with confidence low. Never give medical advice."
)


def looks_health_request(llm_role, text: str) -> Optional[bool]:
    """True/False from the LLM, None when it is unavailable, failed, or not confident (the caller then keeps `general`)."""
    words = text.split()
    if llm_role is None or not getattr(llm_role, "enabled", False) or not (2 <= len(words) <= 80):
        return None
    try:
        out = llm_role.structured(PROMPT, text[:600], IntentCheck, max_tokens=80)
    except Exception as exc:  # noqa: BLE001 - any provider failure means "no opinion"
        log.warning("intent LLM fallback failed: %s", exc)
        return None
    if out.confidence == "low":
        return None
    return bool(out.health_request)
