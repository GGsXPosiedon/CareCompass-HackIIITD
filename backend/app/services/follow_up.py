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
    if facts.n_follow_ups_asked:
        return {
            "en": "What symptoms or care task are you concerned about right now?",
            "hi": "अभी कौन से लक्षण हैं या कौन सा देखभाल का काम चाहिए?",
            "hinglish": "Abhi kya symptoms hain ya kaunsi care ka kaam chahiye?",
        }[lang], OPTIONS[lang]
    return QUESTIONS[lang], OPTIONS[lang]


# One option per real care type, in each language (the same labels as OPTIONS, which the rules already parse when tapped).
AMBIGUITY_OPTION = {
    "paramedic_home_visit": dict(zip(("en", "hi", "hinglish"), (OPTIONS["en"][0], OPTIONS["hi"][0], OPTIONS["hinglish"][0]))),
    "home_nursing": dict(zip(("en", "hi", "hinglish"), (OPTIONS["en"][1], OPTIONS["hi"][1], OPTIONS["hinglish"][1]))),
    "lab_test_home": dict(zip(("en", "hi", "hinglish"), (OPTIONS["en"][2], OPTIONS["hi"][2], OPTIONS["hinglish"][2]))),
    "teleconsultation": dict(zip(("en", "hi", "hinglish"), (OPTIONS["en"][3], OPTIONS["hi"][3], OPTIONS["hinglish"][3]))),
}
AMBIGUITY_TEXT = dialogue.QUESTIONS["ambiguity"]  # one wording, also registered as a dialogue slot so it is recognised as asked


def ambiguity_question(facts: CaseFacts, top: str, runner_up: str) -> tuple[str, list[str]] | None:
    """Two-option question between the two care types the trained head cannot tell apart; None if either has no wording."""
    if top not in AMBIGUITY_OPTION or runner_up not in AMBIGUITY_OPTION:
        return None
    lang = facts.language
    return AMBIGUITY_TEXT[lang], [AMBIGUITY_OPTION[top][lang], AMBIGUITY_OPTION[runner_up][lang]]
