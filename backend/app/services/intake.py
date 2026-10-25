"""Module A: multilingual intake -> structured CaseFacts (tri-state facts).

Concepts come from the SCOPED conversation (see dialogue.analyze): later statements override earlier ones and a new
problem does not inherit old symptoms. The red-flag rules still read the full user text (`safety_text_norm`)."""
from __future__ import annotations

from ..schemas.external import TriageRequest
from ..schemas.internal import CaseFacts
from . import clinical_reference, dialogue
from .lexicon import normalize, resolve_language, strip_prefix


def build_facts(req: TriageRequest) -> CaseFacts:
    a = dialogue.analyze(req)
    all_user = [strip_prefix(t.content) for t in req.conversation_history if t.role == "user" and t.content] + [strip_prefix(req.user_input)]
    scoped = " . ".join(a.scoped_user)
    return CaseFacts(
        text_raw=scoped,
        text_norm=normalize(scoped),
        language=resolve_language(req.language, *all_user),
        concepts=a.concepts,
        evidence=a.evidence,
        n_follow_ups_asked=a.questions_asked,
        latest_input=strip_prefix(req.user_input),
        history=a.scoped_history,
        safety_text_norm=normalize(" . ".join(all_user)),
        analysis=a,
        clinical_details=clinical_reference.extract_details(scoped),
    )
