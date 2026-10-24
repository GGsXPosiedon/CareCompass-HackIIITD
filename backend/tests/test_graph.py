"""Graph + LLM behaviour with a mocked Gemini endpoint (no network)."""
import dataclasses
import json
from datetime import datetime

import httpx
import pytest

from app.config import get_settings
from app.db.repository import CaregiverRepository
from app.schemas.external import TriageRequest
from app.schemas.internal import RouteDecision
from app.services.gemini import GeminiClient
from app.services.matching import Matcher
from app.services.pipeline import Pipeline
from conftest import IST, req

SAFE = {"findings": [], "screening_question": None, "screening_options": []}


def triage(**kw):
    base = {"care_type": None, "confidence": "medium", "red_flags": [], "follow_up_question": None, "answer_options": [],
            "required_skills": [], "patient_member_id": None, "key_facts": [], "profile_facts_used": [], "reasoning": "LLM reasoning."}
    return {**base, **kw}


def make(safety=SAFE, tri=None, *, status=200, raises=False, raw=None, capture=None, **settings):
    s = dataclasses.replace(get_settings(), gemini_api_key="test-key", llm_backend="auto", **settings)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if capture is not None:
            capture.append((request, body))
        if raises:
            raise httpx.ConnectTimeout("t")
        is_safety = "SAFETY SCREENER" in body["systemInstruction"]["parts"][0]["text"]
        payload = raw if raw is not None else (safety if is_safety else tri)
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return httpx.Response(status, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]})

    repo = CaregiverRepository(s.caregivers_path)
    matcher = Matcher(repo, s, now_fn=lambda: datetime(2026, 10, 24, 12, 0, tzinfo=IST))
    return Pipeline(settings=s, repo=repo, matcher=matcher, llm=GeminiClient(s, transport=httpx.MockTransport(handler)))


def run(p, text="mummy ko bukhar hai", **kw):
    return p.triage(TriageRequest(**req(text, **kw)))


# ---- schema enforcement ----------------------------------------------------------------
def test_both_llm_calls_are_schema_constrained_and_key_is_header_only():
    cap = []
    run(make(tri=triage(care_type="paramedic_home_visit", confidence="high"), capture=cap))
    assert len(cap) == 2  # safety + triage, in parallel
    for request, body in cap:
        gen = body["generationConfig"]
        assert gen["responseMimeType"] == "application/json" and gen["temperature"] == 0
        assert gen["responseSchema"]["type"] == "OBJECT"
        assert request.headers["x-goog-api-key"] == "test-key" and "test-key" not in str(request.url)
    systems = {b["systemInstruction"]["parts"][0]["text"][:40] for _, b in cap}
    assert any("SAFETY SCREENER" in x for x in systems) and any("TRIAGE ANALYST" in x for x in systems)


@pytest.mark.parametrize("bad", [
    triage(care_type="surgery_at_home"),                  # enum violation
    triage(care_type="home_nursing", extra_field=1),      # extra key
    triage(care_type="home_nursing", red_flags=["fake"]),  # unknown red flag
    {"care_type": "home_nursing"},                         # missing required keys
    "not json",
])
def test_schema_violations_fall_back_to_deterministic_path(bad):
    p = make(tri=bad) if not isinstance(bad, str) else make(raw=bad)
    r = run(p, "papa ko do din se bukhar hai aur khansi bhi")
    assert r.care_type == "paramedic_home_visit" and r.matched_caregivers  # rules answered


@pytest.mark.parametrize("kw", [{"raises": True}, {"status": 500}])
def test_transport_failures_fall_back(kw):
    r = run(make(tri=triage(care_type="lab_test_home"), **kw), "papa ko do din se bukhar hai aur khansi bhi")
    assert r.care_type == "paramedic_home_visit"


# ---- safety -------------------------------------------------------------------------------
def test_rules_emergency_short_circuits_without_calling_llm():
    cap = []
    r = run(make(tri=triage(care_type="teleconsultation"), capture=cap), "papa ko severe chest pain hai saans nahi aa rahi")
    assert r.care_type == "emergency_112" and cap == []


def test_llm_safety_present_flag_escalates():
    s = {"findings": [{"flag": "stroke_symptoms", "status": "present", "evidence": "ek taraf kamzori"}], "screening_question": None, "screening_options": []}
    r = run(make(safety=s, tri=triage(care_type="teleconsultation")), "mummy ek taraf se kamzor lag rahi hain")
    assert (r.care_type, r.urgency, r.matched_caregivers) == ("emergency_112", "emergency", [])
    assert r.red_flags == ["stroke_symptoms"] and "112" in r.reasoning


def test_llm_triage_red_flag_escalates_even_if_screener_misses():
    r = run(make(tri=triage(care_type="paramedic_home_visit", red_flags=["breathlessness"])), "saans phool rahi hai thodi")
    assert r.care_type == "emergency_112" and "breathlessness" in r.red_flags


def test_possible_flag_asks_danger_sign_question_then_escalates_when_budget_spent():
    s = {"findings": [{"flag": "high_fever_infant", "status": "possible", "evidence": "baby fever"}],
         "screening_question": "Is the baby younger than 3 months?", "screening_options": ["Yes", "No", "Not sure"]}
    p = make(safety=s, tri=triage(care_type="paramedic_home_visit"))
    r = run(p, "bete ko kal raat se bukhar hai")
    assert r.follow_up_question == "Is the baby younger than 3 months?" and r.answer_options == ["Yes", "No", "Not sure"]
    hist = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "q1"}, {"role": "user", "content": "y"}, {"role": "assistant", "content": "q2"}]
    r2 = run(p, "pata nahi", history=hist)
    assert r2.care_type == "emergency_112"


def test_deterministic_model_can_escalate_too(pipeline):
    class Alarmist:
        name = "alarmist"

        def predict(self, facts):
            return RouteDecision("emergency_112", 0.7, [], "alarmist")

    p = make(tri=triage(care_type="paramedic_home_visit"))
    p.router = Alarmist()
    assert run(p).care_type == "emergency_112"


# ---- routing / fusion ------------------------------------------------------------------------
def test_llm_decision_and_reasoning_used_with_skills_enforced():
    p = make(tri=triage(care_type="home_nursing", confidence="high", required_skills=["injection_iv"], reasoning="A Medic will give the IV injection."))
    r = run(p, "doctor ne drip lagane ko bola hai")
    assert r.care_type == "home_nursing" and r.reasoning == "A Medic will give the IV injection."
    assert r.matched_caregivers and all("injection_iv" in p.repo.get(c.caregiver_id).skills for c in r.matched_caregivers)


def test_llm_follow_up_question_and_options():
    p = make(tri=triage(follow_up_question="Kisko madad chahiye, aur kya problem hai?", answer_options=["Bukhar", "Injection", "Test", "Doctor se baat"]))
    r = run(p, "help chahiye")
    assert r.follow_up_question.startswith("Kisko") and len(r.answer_options) == 4 and r.care_type is None


def test_confident_model_overrides_llm_asking():
    # Rules are confident (named procedure) -> no needless question even if the LLM wanted one.
    r = run(make(tri=triage(follow_up_question="What do you need?")), "ghar pe injection lagwana hai")
    assert r.care_type == "home_nursing"


def test_agree_or_ask_policy_asks_on_disagreement():
    p = make(tri=triage(care_type="teleconsultation", confidence="medium"), fusion_policy="agree_or_ask")
    r = run(p, "ghar pe injection lagwana hai")
    assert r.follow_up_question and r.care_type is None


def test_model_first_policy_prefers_confident_model():
    p = make(tri=triage(care_type="teleconsultation", confidence="high"), fusion_policy="model_first")
    assert run(p, "ghar pe injection lagwana hai").care_type == "home_nursing"


def test_follow_up_cap_forces_safe_default():
    p = make(tri=triage(follow_up_question="Again?"))
    hist = [{"role": "user", "content": "help"}, {"role": "assistant", "content": "q1"}, {"role": "user", "content": "x"}, {"role": "assistant", "content": "q2"}]
    r = run(p, "pata nahi", history=hist)
    assert r.follow_up_question is None and r.care_type == "paramedic_home_visit"


def test_profile_is_sent_inside_fenced_case():
    cap = []
    p = make(tri=triage(care_type="paramedic_home_visit", confidence="high"), capture=cap)
    body = req("papa ko bukhar hai")
    body["patient_context"] = {"active_member_id": "m1", "members": [
        {"id": "m1", "name": "Ramesh", "relation": "Father", "age": 68, "conditions": ["Type 2 diabetes"], "allergies": ["Penicillin"]}]}
    p.triage(TriageRequest(**body))
    sent = cap[0][1]["contents"][0]["parts"][0]["text"]
    assert "Type 2 diabetes" in sent and "<user_message>" in sent and "PROFILE:" in sent


def test_trace_explains_every_step():
    t = make(tri=triage(care_type="lab_test_home", confidence="high")).trace(TriageRequest(**req("ghar pe blood test karwana hai")))
    nodes = [x["node"] for x in t["trace"]]
    assert nodes[:2] == ["intake", "rules_safety"] and {"classify", "llm_safety", "llm_triage"} <= set(nodes)
    assert nodes[-3:] == ["fuse", "match", "respond"] and t["decision"]["agreement"] is True


def test_llm_off_without_key(pipeline):
    assert pipeline.llm.enabled is False
    t = pipeline.trace(TriageRequest(**req("mummy ko bukhar hai ghar pe dikhana hai")))
    assert any("skipped" in x["detail"] for x in t["trace"] if x["node"] == "llm_triage")


def test_graph_renders():
    assert "fuse" in make(tri=triage()).graph.mermaid()
