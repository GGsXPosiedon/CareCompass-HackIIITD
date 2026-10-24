"""Module D: routing model interface.

The pipeline only talks to `Router.predict`. Today the default is a transparent rule-based
placeholder; the real model (TF-IDF/embeddings classifier, optional LLM vote) plugs in later
by implementing the same interface and setting ROUTER_BACKEND.
"""
from __future__ import annotations

from typing import Protocol

from ..config import URGENCY_BY_CARE_TYPE, get_settings
from ..schemas.internal import CaseFacts, RouteDecision
from .lexicon import group_of


class Router(Protocol):
    name: str

    def predict(self, facts: CaseFacts) -> RouteDecision: ...


def urgency_for(care_type: str) -> str:
    return URGENCY_BY_CARE_TYPE[care_type]


class RuleRouter:
    """Placeholder baseline: precedence rules over the concept lexicon. Not a trained model."""

    name = "rules"

    def predict(self, facts: CaseFacts) -> RouteDecision:
        present = {c for c in facts.concepts if facts.present(c)}
        by_group: dict[str, set[str]] = {}
        for c in present:
            by_group.setdefault(group_of(c), set()).add(c)

        nursing = by_group.get("nursing", set())
        lab = by_group.get("lab", set())
        consult = by_group.get("consult", set())
        symptoms = by_group.get("symptom", set())
        home = "home_visit_request" in present

        if nursing:
            return RouteDecision("home_nursing", 0.9, sorted(nursing), self.name)
        if "consult" in present and "report_review" in present:
            return RouteDecision("teleconsultation", 0.85, sorted(consult), self.name)
        if lab:
            return RouteDecision("lab_test_home", 0.85, sorted(lab), self.name)
        if "consult" in present and not home:
            return RouteDecision("teleconsultation", 0.8, sorted(consult | symptoms), self.name)
        if symptoms or ("consult" in present and home):
            # BP/sugar check and general complaints -> Medic visit
            return RouteDecision("paramedic_home_visit", 0.75 if home else 0.65, sorted(symptoms), self.name)
        return RouteDecision(None, 0.0, [], self.name)


class _NotImplementedRouter:
    def __init__(self, name: str):
        self.name = name

    def predict(self, facts: CaseFacts) -> RouteDecision:  # pragma: no cover
        raise NotImplementedError(f"Router backend '{self.name}' is not implemented yet")


def build_router(name: str | None = None) -> Router:
    """Deterministic classifier slot. Today: transparent rules. Later: your trained model.

    To plug a model in: implement `predict(facts) -> RouteDecision` (care_type may be None or
    "emergency_112"; confidence in [0,1]) and register it here, then set ROUTER_BACKEND=<name>.
    The graph fuses it with the LLM according to FUSION_POLICY (see app/graph/nodes.py::fuse).
    """
    name = name or get_settings().router_backend
    if name in ("rules", "auto"):  # "auto" kept for older .env files
        return RuleRouter()
    return _NotImplementedRouter(name)
