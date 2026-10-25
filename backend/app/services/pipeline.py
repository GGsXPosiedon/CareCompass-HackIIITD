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
from .llm_router import build_llm
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
        llm: Optional[object] = None,
    ):
        self.settings = settings or get_settings()
        self.router = router or build_router(self.settings.router_backend)  # deterministic model slot
        self.encoder = getattr(self.router, "models", None)  # EncoderModels when ROUTER_BACKEND=trained and the model folder is usable
        self.safety = safety or get_safety_engine()
        self.repo = repo or get_repository()
        self.matcher = matcher or Matcher(self.repo, self.settings)
        self.llm = llm if llm is not None else build_llm(self.settings)
        chains = getattr(self.llm, "chains", None)
        if chains is not None:  # one line at startup so the server console shows what the LLM layer will actually use
            log.warning("LLM providers: %s", chains if getattr(self.llm, "enabled", False) else
                        "NONE ENABLED - replies use fallback rules (check backend/.env keys and LLM_BACKEND, and Windows environment variables that override it)")
        from ..graph import TriageGraph  # local import: graph imports this module for typing

        self.graph = TriageGraph(self)

    def run(self, req: TriageRequest) -> tuple[TriageResponse, dict]:
        resp, state = self.graph.run(req)
        resp.response_language = state["facts"].language
        if state["rule_safety"].requires_emergency:
            resp.response_source = "safety_rules"
        else:
            resp.response_source = "gemini" if state.get("llm_triage") is not None else "rules"
            # Dialogue turns can intentionally skip triage; missing output is not a failed call.
            if self.llm.enabled and any(node in state and state[node] is None for node in ("llm_triage", "llm_safety")):
                resp.service_notice = {
                    "en": "Some AI checks are temporarily unavailable, so this reply may be limited.",
                    "hi": "AI की कुछ जाँच अभी उपलब्ध नहीं हैं, इसलिए यह जवाब अधूरा हो सकता है।",
                    "hinglish": "AI ki kuch checks abhi nahi ho paayi, isliye is jawab mein jaankari kam ho sakti hai.",
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
