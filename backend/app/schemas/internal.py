"""Internal models. Never returned directly over the API."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FactStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"  # explicitly denied by the patient
    UNKNOWN = "unknown"  # never mentioned (NOT the same as absent)
    UNCERTAIN = "uncertain"


@dataclass
class CaseFacts:
    text_raw: str
    text_norm: str
    language: str  # en | hi | hinglish
    concepts: dict[str, FactStatus] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    n_follow_ups_asked: int = 0
    latest_input: str = ""
    history: list = field(default_factory=list)  # [{'role','content'}]
    patient_context: Optional[dict] = None  # sanitised, client-supplied profile data
    safety_text_norm: str = ""  # ALL user text; the red-flag rules read this, never the scoped text
    analysis: Optional[object] = None  # dialogue.Analysis (intent, scoped context, slots)

    def present(self, concept: str) -> bool:
        return self.concepts.get(concept) == FactStatus.PRESENT


@dataclass
class SafetyResult:
    requires_emergency: bool
    flags: list[str]
    rule_ids: list[str]
    ruleset_version: str
    source: str = "rules"  # rules | model_guard


@dataclass
class RouteDecision:
    care_type: Optional[str]  # None => cannot decide yet
    confidence: float
    evidence: list[str]
    source: str
    # Optional extras filled by LLM routers (all validated by the pipeline before use)
    red_flags: list[str] = field(default_factory=list)
    follow_up_question: Optional[str] = None
    answer_options: Optional[list[str]] = None
    required_skills: list[str] = field(default_factory=list)
    reasoning: str = ""
    profile_used: bool = False


@dataclass
class Candidate:
    caregiver_id: str
    score: float
    reason: str
    components: dict[str, float]
