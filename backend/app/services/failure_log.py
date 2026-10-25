"""Append-only log of turns worth a human look, so mentor/demo edge cases become tests instead of lost screenshots.

Logged: generic 'I can help with health...' replies, forced fallback routes, LLM failures, and semantic-net escalations.
Stores the user's raw text locally in backend/logs/failures.jsonl (git-ignored). Turn off with FAILURE_LOG=off.
Review with:  python -m eval.review_failures
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "logs" / "failures.jsonl"


def reasons(resp, state: dict) -> list[str]:
    out = []
    trace = state.get("trace", [])
    a = getattr(state["facts"], "analysis", None)
    if a is not None and getattr(a, "act", "") == "general":
        out.append("general_reply")
    d = state.get("decision") or {}
    if d.get("basis") == "fallback":
        out.append("fallback_route")
    if any("failed" in t.get("detail", "") for t in trace):
        out.append("llm_failed")
    if any("skipped (LLM off)" in t.get("detail", "") for t in trace):
        out.append("llm_off")  # no usable provider: no key found / LLM_BACKEND=off / every chain empty
    rs = state.get("rule_safety")
    if rs is not None and getattr(rs, "source", "") == "semantic":
        out.append("semantic_escalation")
    return out


def record(req, resp, state: dict) -> None:
    if os.getenv("FAILURE_LOG", "on").lower() in ("off", "0", "false"):
        return
    try:
        why = reasons(resp, state)
        if not why:
            return
        PATH.parent.mkdir(exist_ok=True)
        row = {"ts": int(time.time()), "why": why, "user_input": req.user_input,
               "history": [h.model_dump() if hasattr(h, "model_dump") else h for h in (req.conversation_history or [])][-6:],
               "llm_errors": [f"{t.get('node')}: {t.get('detail', '')[:160]}" for t in state.get("trace", []) if "failed" in t.get("detail", "") or "skipped (LLM off)" in t.get("detail", "")],
               "care_type": resp.care_type, "follow_up": resp.follow_up_question, "red_flags": resp.red_flags}
        with PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # logging must never break a triage
        pass
