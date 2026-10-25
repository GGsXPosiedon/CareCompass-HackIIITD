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


# An explicit ask for emergency help ("ambulance chahiye", "this is an emergency", the app's own 'Emergency' answer option) is
# honoured even when no symptom is named. It carries no red-flag label (the API enum stays unchanged); it only ever raises.
_EXPLICIT_EMERGENCY = re.compile(
    r"\bambulance\b|\bambulans\b|(?<!not an )(?<!not a )(?<!no )(?<!not )\bemerg\w*\b|\b112\b|\b108\b|एम्बुलेंस|एंबुलेंस|इमरजेंसी|आपातकाल|आपात स्थिति"
)

# Remove only explicitly historical diagnosis labels, never their associated current symptoms.
# "Had a stroke last year, now one side is weak" still fires the current weakness rule.
_PAST_DIAGNOSIS = re.compile(
    r"\b(?:history of|previous|past|old|prior) (?:a )?(?:stroke|heart attack)\b|"
    r"\b(?:had (?:a )?)?(?:stroke|heart attack) (?:last year|\d+ years? ago)\b"
)


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

    def denied_flags(self, text: str) -> list[str]:
        """Red flags the user explicitly denied ("seene me dard nahi hai", "no breathing problem"): a pattern matched but only negated.
        Used only to avoid asking a danger-sign question the person has already answered."""
        out: list[str] = []
        for rule in self._rules:
            pats = list(rule["patterns"]) + [rx for g in rule["all_of"] for rx in g]
            hits = [m for rx in pats for m in rx.finditer(text)]
            if hits and not rule["negation_safe"] and all(is_negated(text, m.start(), m.end()) for m in hits):
                out.append(rule["flag"])
        return out

    def evaluate(self, facts: CaseFacts) -> SafetyResult:
        text = _PAST_DIAGNOSIS.sub("past medical condition", facts.safety_text_norm or facts.text_norm)
        flags: list[str] = []
        ids: list[str] = []
        for rule in self._rules:
            if self._fires(rule, text):
                if rule["flag"] not in flags:
                    flags.append(rule["flag"])
                ids.append(rule["id"])
        if not flags:
            t = text
            if any(not is_negated(t, m.start(), m.end()) for m in _EXPLICIT_EMERGENCY.finditer(t)):
                return SafetyResult(True, [], ["RF-EX-01"], self.version, "rules")
        if not flags:  # meaning-based net: only runs when no rule fired, only ever raises urgency
            from .semantic_safety import get_semantic_safety

            net = get_semantic_safety() if self.semantic else None
            hit = net.check(text) if net else None
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
