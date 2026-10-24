"""Pipeline facade: owns the components and runs the LangGraph triage graph.

The graph (app/graph) is the only place a TriageResponse is assembled, so contract invariants hold
everywhere. Components are attributes so tests/ops can swap them (e.g. pipeline.router = MyModel()).
"""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

from ..config import Settings, get_settings
from ..db.repository import CaregiverRepository, get_repository
from ..schemas.external import TriageRequest, TriageResponse
from .gemini import GeminiClient
from .matching import Matcher
from .routing import Router, build_router
from .safety import SafetyEngine, get_safety_engine

log = logging.getLogger("carecompass.audit")


class Pipeline:
    def __init__(
        self,
        settings: Settings | None = None,
        router: Router | None = None,
        safety: SafetyEngine | None = None,
        repo: CaregiverRepository | None = None,
        matcher: Matcher | None = None,
        llm: Optional[GeminiClient] = None,
    ):
        self.settings = settings or get_settings()
        self.router = router or build_router(self.settings.router_backend)  # deterministic model slot
        self.safety = safety or get_safety_engine()
        self.repo = repo or get_repository()
        self.matcher = matcher or Matcher(self.repo, self.settings)
        self.llm = llm if llm is not None else GeminiClient(self.settings)
        from ..graph import TriageGraph  # local import: graph imports this module for typing

        self.graph = TriageGraph(self)

    def run(self, req: TriageRequest) -> tuple[TriageResponse, dict]:
        resp, state = self.graph.run(req)
        resp.response_language = state["facts"].language
        if state["rule_safety"].requires_emergency:
            resp.response_source = "safety_rules"
        else:
            resp.response_source = "gemini" if state.get("llm_triage") is not None else "rules"
            if state.get("llm_triage") is None or state.get("llm_safety") is None:
                resp.service_notice = {
                    "en": "Gemini could not complete all checks. Limited fallback rules were used for this reply.",
                    "hi": "Gemini उपलब्ध नहीं है या उत्तर सही नहीं था। यह जवाब सीमित वैकल्पिक नियमों पर आधारित है।",
                    "hinglish": "Gemini available nahi hai ya response sahi nahi tha. Yeh reply limited fallback rules se hai.",
                }[state["facts"].language]
        h = hashlib.sha256(state["facts"].text_norm.encode()).hexdigest()[:10]  # no raw text in logs
        log.info("case=%s care_type=%s flags=%s path=%s", h, resp.care_type, resp.red_flags, [t["node"] for t in state["trace"]])
        from .failure_log import record

        record(req, resp, state)
        return resp, state

    def triage(self, req: TriageRequest) -> TriageResponse:
        return self.run(req)[0]

    def trace(self, req: TriageRequest) -> dict:
        resp, state = self.run(req)
        return {
            "response": resp.to_wire(),
            "decision": state.get("decision"),
            "trace": state["trace"],
            "components": {
                "classifier": self.router.name,
                "llm": self.llm.model if self.llm and self.llm.enabled else "off",
                "ruleset": self.safety.version,
                "fusion_policy": self.settings.fusion_policy,
            },
        }
