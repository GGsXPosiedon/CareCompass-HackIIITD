"""Deterministic, versioned safety engine. Runs BEFORE routing and guards model output.

Design rules:
* Independent of any ML/LLM output.
* When unsure, escalate (under-triage is the costly error).
* Negation only suppresses a flag for an immediate explicit cue ("no chest pain").
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache

from ..config import get_settings
from ..schemas.internal import CaseFacts, RouteDecision, SafetyResult
from .lexicon import is_negated


class SafetyEngine:
    def __init__(self, rules_path: str | None = None, semantic: bool = True):
        self.semantic = semantic
        path = rules_path or get_settings().redflag_rules_path
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
        self.version: str = spec["version"]
        self._rules = []
        for r in spec["rules"]:
            self._rules.append(
                {
                    "id": r["id"],
                    "flag": r["flag"],
                    "negation_safe": bool(r.get("negation_safe")),
                    "patterns": [re.compile(unicodedata.normalize("NFKC", p)) for p in r.get("patterns", [])],
                    "all_of": [[re.compile(unicodedata.normalize("NFKC", p)) for p in group] for group in r.get("all_of", [])],
                }
            )

    def _fires(self, rule: dict, text: str) -> bool:
        for rx in rule["patterns"]:
            for m in rx.finditer(text):
                if rule["negation_safe"] or not is_negated(text, m.start(), m.end()):
                    return True
        groups = rule["all_of"]
        if groups and all(
            any(
                any(rule["negation_safe"] or not is_negated(text, m.start(), m.end()) for m in rx.finditer(text))
                for rx in group
            )
            for group in groups
        ):
            return True
        return False

    def evaluate(self, facts: CaseFacts) -> SafetyResult:
        flags: list[str] = []
        ids: list[str] = []
        for rule in self._rules:
            if self._fires(rule, facts.safety_text_norm or facts.text_norm):
                if rule["flag"] not in flags:
                    flags.append(rule["flag"])
                ids.append(rule["id"])
        if not flags:  # meaning-based net: only runs when no rule fired, only ever raises urgency
            from .semantic_safety import get_semantic_safety

            net = get_semantic_safety() if self.semantic else None
            hit = net.check(facts.safety_text_norm or facts.text_norm) if net else None
            if hit:
                return SafetyResult(True, [hit.flag], [f"SEM-{hit.flag}"], self.version, "semantic")
        return SafetyResult(bool(flags), flags, ids, self.version, "rules")

    def guard(self, decision: RouteDecision, current: SafetyResult) -> SafetyResult:
        """A model may RAISE urgency to emergency; it can never lower a rules decision."""
        if current.requires_emergency:
            return current
        if decision.care_type == "emergency_112":
            return SafetyResult(True, [], ["MODEL-GUARD"], self.version, "model_guard")
        return current


@lru_cache
def get_safety_engine() -> SafetyEngine:
    return SafetyEngine()
