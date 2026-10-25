"""LangGraph wiring.

            ┌──────────┐   ┌──────────────┐  fired   ┌───────────┐
  START ──▶ │  intake  │──▶│ rules_safety │ ───────▶ │ emergency │──▶ END
            └──────────┘   └──────┬───────┘          └───────────┘
                                  │ clear
                           ┌──────▼──────┐  chat / refusal / stop / frustration / slot question
                           │  converse   │ ──▶ reply_guard (LLM safety screen) ──▶ dialogue_reply ──▶ END
                           └──────┬──────┘
                                  │ proceed (parallel fan-out)  ▲
                ┌─────────────────┼──────────────────┐        │
                ▼                 ▼                  ▼        │
           ┌─────────┐     ┌────────────┐     ┌────────────┐  │
           │classify │     │ llm_safety │     │ llm_triage │  │
           │(model   │     │ (Gemini,   │     │ (Gemini,   │  │
           │ slot)   │     │  recall)   │     │  service)  │  │
           └────┬────┘     └─────┬──────┘     └─────┬──────┘  │
                └────────────────┼──────────────────┘         │
                                 ▼                            │
                            ┌─────────┐  escalate ────────────┘
                            │  fuse   │  ask ──▶ follow_up ──▶ END
                            └────┬────┘
                                 │ route
                                 ▼
                            ┌─────────┐   ┌─────────┐
                            │  match  │──▶│ respond │──▶ END
                            └─────────┘   └─────────┘
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from ..schemas.external import TriageRequest, TriageResponse
from .nodes import Nodes
from .state import TriageState

if TYPE_CHECKING:
    from ..services.pipeline import Pipeline


class TriageGraph:
    def __init__(self, pipe: "Pipeline"):
        n = Nodes(pipe)
        g = StateGraph(TriageState)
        for name in ("intake", "rules_safety", "converse", "reply_guard", "dialogue_reply", "classify", "llm_safety", "llm_triage", "fuse",
                     "emergency", "follow_up", "match", "respond"):
            g.add_node(name, getattr(n, name))
        g.add_edge(START, "intake")
        g.add_edge("intake", "rules_safety")
        g.add_conditional_edges("rules_safety", n.after_rules, ["emergency", "converse"])
        g.add_conditional_edges("converse", n.after_converse, ["reply_guard", "classify", "llm_safety", "llm_triage"])
        g.add_conditional_edges("reply_guard", n.after_guard, ["emergency", "follow_up", "dialogue_reply", "match"])
        g.add_edge(["classify", "llm_safety", "llm_triage"], "fuse")
        g.add_conditional_edges("fuse", n.after_fuse, ["emergency", "follow_up", "match"])
        g.add_edge("match", "respond")
        for terminal in ("emergency", "dialogue_reply", "follow_up", "respond"):
            g.add_edge(terminal, END)
        self.compiled = g.compile()

    def run(self, req: TriageRequest) -> tuple[TriageResponse, dict]:
        state = self.compiled.invoke({"request": req, "trace": []})
        return state["response"], state

    def mermaid(self) -> str:
        return self.compiled.get_graph().draw_mermaid()
