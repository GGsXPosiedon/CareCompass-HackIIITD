"""Module D: routing model interface.

The pipeline only talks to `Router.predict`. Today the default is a transparent rule-based
placeholder; the real model (TF-IDF/embeddings classifier, optional LLM vote) plugs in later
by implementing the same interface and setting ROUTER_BACKEND.
"""
from __future__ import annotations

import math

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
        if "named_condition" in present:
            # a known condition with no symptom, procedure or request named: a doctor consultation is the safe, routine default
            return RouteDecision("teleconsultation", 0.6, ["named_condition"], self.name)
        return RouteDecision(None, 0.0, [], self.name)


class TrainedRouter:
    """Classifier slot, trained: explicit rule evidence (procedure / lab / consult words) first, the e5 head for everything else.

    The e5 head never returns emergency_112 by itself (its argmax over-triages 4 of 57 non-emergencies); it only hands an
    emergency score to the graph, which turns a high score into a danger-sign question or, very high, the 112 path."""

    name = "trained"

    def __init__(self, models, fallback: Router | None = None):
        self.models, self.rules = models, fallback or RuleRouter()

    def predict(self, facts: CaseFacts) -> RouteDecision:
        text = facts.text_norm or facts.latest_input
        whole = facts.safety_text_norm or text
        es = self.models.emergency_score(facts.latest_input or text, whole)
        rd = self.rules.predict(facts)
        if rd.care_type and rd.confidence >= 0.75:
            rd.emergency_score, rd.source = es, "rules+encoder"
            return rd
        sc = self.models.scores(text)
        ranked = sorted(((p, c) for c, p in sc.probs.items() if c != "emergency_112"), reverse=True)
        p, c = ranked[0]
        care = None if c == "ask_followup" else c
        ev = [f"e5 head {c}={p:.2f}", f"emergency score {es:.2f}"]
        # runner-up among real care types (same definition as scripts/calibrate_ambiguity.py)
        real = [(q, k) for q, k in ranked if k != "ask_followup"]
        runner = margin = None
        if care and len(real) >= 2 and real[1][0] > 0:
            runner, margin = real[1][1], math.log(real[0][0] / real[1][0])
        if rd.care_type and care and rd.care_type != care:
            return RouteDecision(rd.care_type, rd.confidence, rd.evidence + ev, "rules+encoder", emergency_score=es)
        return RouteDecision(care, p, ev, "encoder", emergency_score=es, runner_up=runner, margin=margin)


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
    if name == "trained":
        from .encoder_models import EncoderModels

        models = EncoderModels.maybe(get_settings().encoder_path)
        return TrainedRouter(models) if models else RuleRouter()
    return _NotImplementedRouter(name)
