"""Module B: follow-up policy. Ask only when the intent is underspecified; never repeat; cap questions."""
from __future__ import annotations

from ..config import get_settings
from ..schemas.internal import CaseFacts, RouteDecision
from . import dialogue

QUESTIONS = {
    "en": "Happy to help. What kind of care do you need?",
    "hi": "मैं मदद करूँगा। आपको किस तरह की देखभाल चाहिए?",
    "hinglish": "Zaroor madad karunga. Aapko kis tarah ki care chahiye?",
}
OPTIONS = {
    "en": ["Fever, pain or weakness check at home", "Injection or dressing at home", "Lab test at home", "Talk to a doctor online"],
    "hi": ["घर पर बुखार, दर्द या कमजोरी की जांच", "घर पर इंजेक्शन या ड्रेसिंग", "घर पर लैब टेस्ट", "डॉक्टर से ऑनलाइन बात"],
    "hinglish": ["Ghar pe bukhar, dard ya kamzori check", "Ghar pe injection ya dressing", "Ghar pe lab test", "Doctor se online baat"],
}


def should_ask(facts: CaseFacts, decision: RouteDecision) -> bool:
    return decision.care_type is None and facts.n_follow_ups_asked < get_settings().max_follow_ups


def next_question(facts: CaseFacts) -> tuple[str, list[str]]:
    """Symptom-specific slot question when we know the symptom, otherwise the generic 'what care do you need?'."""
    a = facts.analysis
    if a is not None:
        q = dialogue.next_slot_question(a)
        if q:
            return q.message, q.options or []
    lang = facts.language
    return QUESTIONS[lang], OPTIONS[lang]
