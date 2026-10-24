"""Module A: multilingual intake -> structured CaseFacts (tri-state facts)."""
from __future__ import annotations

from ..schemas.external import TriageRequest
from ..schemas.internal import CaseFacts
from .lexicon import extract_concepts, normalize, resolve_language, strip_prefix


def build_facts(req: TriageRequest) -> CaseFacts:
    user_turns = [strip_prefix(t.content) for t in req.conversation_history if t.role == "user" and t.content]
    latest = strip_prefix(req.user_input)
    all_user_text = user_turns + [latest]
    combined = " . ".join(all_user_text)
    norm = normalize(combined)
    concepts, evidence = extract_concepts(norm)
    # A new question after a recommendation starts a fresh clarification budget.
    last_decision = max((i for i, t in enumerate(req.conversation_history)
                         if t.role == "assistant" and t.kind in ("recommendation", "emergency")), default=-1)
    return CaseFacts(
        text_raw=combined,
        text_norm=norm,
        language=resolve_language(req.language, *all_user_text),
        concepts=concepts,
        evidence=evidence,
        n_follow_ups_asked=sum(1 for t in req.conversation_history[last_decision + 1:] if t.role == "assistant" and t.content),
        latest_input=latest,
        history=[{"role": t.role, "content": t.content} for t in req.conversation_history if t.content],
        patient_context=req.patient_context.model_dump() if req.patient_context else None,
    )
