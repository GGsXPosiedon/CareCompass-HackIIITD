"""Strict schemas for everything an LLM is allowed to return.

* `extra="forbid"`: unknown keys are a validation error (the call is treated as failed -> fallback).
* Every categorical field is a closed Literal (the official enums), so a hallucinated label cannot pass.
* The same models generate the Gemini `responseSchema` (see `gemini_schema`), so the model is
  constrained at generation time AND re-validated here (defence in depth).
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from .external import RedFlag

Skill = Literal[
    "injection_im", "injection_iv", "wound_dressing", "catheter_care", "nebulization", "vitals_monitoring",
    "bp_sugar_check", "elderly_care", "post_surgical_care", "sample_collection", "home_phlebotomy",
    "teleconsultation", "prescription", "report_review",
]
LLMCareType = Literal["paramedic_home_visit", "home_nursing", "lab_test_home", "teleconsultation", "emergency_112"]
Confidence = Literal["low", "medium", "high"]


def Text(n: int):  # noqa: N802 - clip over-long text instead of rejecting a valid answer
    return Annotated[str, BeforeValidator(lambda v: " ".join(v.split())[:n] if isinstance(v, str) else v)]


def Capped(n: int):  # noqa: N802 - keep the first n items of a list; item types are still validated
    return BeforeValidator(lambda v: v[:n] if isinstance(v, list) else v)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FlagFinding(_Strict):
    flag: RedFlag
    status: Literal["present", "possible"] = Field(
        description="present = described as happening now; possible = could be happening but the message is unclear")
    evidence: Text(160) = Field( description="short quote/paraphrase of the words that raised it")


class SafetyReview(_Strict):
    """Output of the safety screener node (recall-oriented, red flags only)."""

    findings: Annotated[list[FlagFinding], Capped(9)] = Field(default_factory=list)
    screening_question: Optional[Text(220)] = Field(
        default=None,
        description="ONE yes/no danger-sign question when a flag is only 'possible'; otherwise null")
    screening_options: Annotated[list[Text(40)], Capped(4)] = Field(default_factory=list)


class TriageAssessment(_Strict):
    """Output of the triage analyst node."""

    care_type: Optional[LLMCareType] = Field(description="null only when one more fact is genuinely needed")
    confidence: Confidence
    red_flags: Annotated[list[RedFlag], Capped(9)] = Field(default_factory=list)
    follow_up_question: Optional[Text(220)] = None
    answer_options: Annotated[list[Text(40)], Capped(4)] = Field(default_factory=list)
    required_skills: Annotated[list[Skill], Capped(6)] = Field(default_factory=list)
    patient_member_id: Optional[Text(40)] = Field(default=None,
                                             description="id from PROFILE of the person who needs care, if identifiable")
    key_facts: Annotated[list[Text(80)], Capped(6)] = Field(default_factory=list, description="short facts from the message that drove the decision")
    profile_facts_used: Annotated[list[Text(80)], Capped(6)] = Field(default_factory=list)
    reasoning: Text(420) = Field(description="1-2 plain sentences for the family, in their language; no diagnosis")


# ---- pydantic JSON schema -> Gemini responseSchema (OpenAPI subset) ------------------------
_TYPE = {"string": "STRING", "integer": "INTEGER", "number": "NUMBER", "boolean": "BOOLEAN", "array": "ARRAY", "object": "OBJECT"}


def _convert(node: dict, defs: dict) -> dict:
    if "$ref" in node:
        return _convert(defs[node["$ref"].split("/")[-1]], defs)
    if "anyOf" in node:  # Optional[X] -> X + nullable
        opts = [o for o in node["anyOf"] if o.get("type") != "null"]
        out = _convert(opts[0], defs)
        if len(opts) < len(node["anyOf"]):
            out["nullable"] = True
        if node.get("description"):
            out["description"] = node["description"]
        return out
    out: dict[str, Any] = {}
    if "enum" in node or "const" in node:
        out["type"] = "STRING"
        out["enum"] = list(node.get("enum") or [node["const"]])
    else:
        out["type"] = _TYPE[node["type"]]
    if node.get("description"):
        out["description"] = node["description"]
    if out["type"] == "ARRAY":
        out["items"] = _convert(node["items"], defs)
        if "maxItems" in node:
            out["maxItems"] = node["maxItems"]
    if out["type"] == "OBJECT":
        props = node.get("properties", {})
        out["properties"] = {k: _convert(v, defs) for k, v in props.items()}
        out["required"] = list(props)  # ask for every key; Optional ones may be null
        out["propertyOrdering"] = list(props)
    return out


def gemini_schema(model: type[BaseModel]) -> dict:
    js = model.model_json_schema()
    return _convert(js, js.get("$defs", {}))
