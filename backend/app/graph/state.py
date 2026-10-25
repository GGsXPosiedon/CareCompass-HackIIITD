"""Shared LangGraph state. Parallel nodes write DISTINCT keys; list keys use an append reducer."""
from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict

from ..schemas.external import TriageRequest, TriageResponse
from ..schemas.internal import CaseFacts, RouteDecision, SafetyResult
from ..schemas.llm import SafetyReview, TriageAssessment


class TriageState(TypedDict, total=False):
    request: TriageRequest
    facts: CaseFacts
    rule_safety: SafetyResult            # deterministic red-flag engine
    dialogue: Any                        # dialogue.DialogueDecision (reply | ask | proceed)
    emergency_score: Optional[float]     # trained binary emergency head (None when no encoder configured)
    det: RouteDecision                   # deterministic classifier slot (rules now, trained model later)
    llm_safety: Optional[SafetyReview]   # Gemini safety screener
    llm_triage: Optional[TriageAssessment]  # Gemini triage analyst
    decision: dict[str, Any]             # fused decision (see nodes.fuse)
    response: TriageResponse
    candidates: list                     # matcher output with score components (for /trace)
    trace: Annotated[list[dict], operator.add]
