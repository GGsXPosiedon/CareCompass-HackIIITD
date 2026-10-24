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
from app.schemas.llm import SafetyReview
from app.services.gemini import GeminiClient
from app.services.matching import Matcher
from app.services.pipeline import Pipeline
from conftest import IST, req, seed_settings

SAFE = {"findings": [], "screening_question": None, "screening_options": []}


def triage(**kw):
    base = {"care_type": None, "confidence": "medium", "red_flags": [], "follow_up_question": None, "answer_options": [],
            "required_skills": [], "patient_member_id": None, "key_facts": [], "profile_facts_used": [], "reasoning": "LLM reasoning."}
    return {**base, **kw}


def make(safety=SAFE, tri=None, *, status=200, raises=False, raw=None, capture=None, **settings):
    s = dataclasses.replace(seed_settings(), gemini_api_key="test-key", llm_backend="auto", **settings)

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


def test_all_llm_required_skills_are_hard_filters_and_never_relaxed():
    skills = ["injection_iv", "catheter_care"]
    p = make(tri=triage(care_type="home_nursing", required_skills=skills))
    result = run(p, "Need nursing help", location=None)
    assert result.matched_caregivers
    assert all(set(skills) <= p.repo.get(c.caregiver_id).skills for c in result.matched_caregivers)
    p = make(tri=triage(care_type="home_nursing", required_skills=["nebulization", "catheter_care", "post_surgical_care"]))
    assert run(p, "Need nursing help", location=None).matched_caregivers == []


def test_gemini_urgency_can_be_scheduled_for_a_routine_consultation():
    p = make(tri=triage(care_type="teleconsultation", urgency="scheduled"))
    assert run(p, "Routine doctor follow-up tomorrow").urgency == "scheduled"


def test_gemini_emergency_urgency_alone_escalates_and_never_returns_matches():
    p = make(tri=triage(care_type="teleconsultation", urgency="emergency"))
    result = run(p, "unclear need")
    assert result.care_type == "emergency_112" and not result.matched_caregivers


def test_llm_follow_up_question_and_options():
    p = make(tri=triage(follow_up_question="Kisko madad chahiye, aur kya problem hai?", answer_options=["Bukhar", "Injection", "Test", "Doctor se baat"]))
    r = run(p, "help chahiye")
    assert r.follow_up_question.startswith("Kisko") and len(r.answer_options) == 4 and r.care_type is None


def test_llm_first_respects_contextual_question_even_when_rules_are_confident():
    r = run(make(tri=triage(follow_up_question="What do you need?")), "ghar pe injection lagwana hai")
    assert r.follow_up_question == "What do you need?" and r.care_type is None


def test_short_answer_and_original_case_are_sent_to_gemini():
    cap = []
    p = make(tri=triage(care_type="teleconsultation", reasoning="A doctor can discuss the reports."), capture=cap)
    history = [{"role": "user", "content": "I need help with reports"},
               {"role": "assistant", "content": "Do you want a doctor to review them?", "kind": "follow_up"}]
    result = run(p, "Yes", history=history)
    assert result.care_type == "teleconsultation" and result.response_source == "gemini"
    for _, body in cap:
        case = body["contents"][0]["parts"][0]["text"]
        assert "I need help with reports" in case and "Do you want a doctor to review them?" in case
        assert "<user_message>\nYes\n</user_message>" in case


def test_repeated_gemini_question_is_replaced_with_a_different_question():
    p = make(tri=triage(follow_up_question="What do you need?"))
    result = run(p, "help", history=[{"role": "assistant", "content": "What do you need?"}])
    assert result.follow_up_question and result.follow_up_question != "What do you need?"


def test_gemini_failure_is_visible_in_response():
    result = run(make(status=503), "need a blood test")
    assert result.response_source == "rules" and result.service_notice


def test_gemini3_uses_thinking_level_and_retries_temporary_server_failure():
    settings = dataclasses.replace(get_settings(), gemini_api_key="test", gemini_model="gemini-3.5-flash")
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(SAFE)}]}}]})
    output = GeminiClient(settings, transport=httpx.MockTransport(handler)).structured("SAFETY SCREENER", "Hello", SafetyReview)
    assert output.findings == [] and len(requests) == 2
    assert requests[0]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}
    assert requests[0]["generationConfig"]["maxOutputTokens"] >= 4096


def test_recommendation_starts_new_follow_up_budget():
    p = make(tri=triage(follow_up_question="What would you like help with now?"))
    history = [{"role": "assistant", "content": "q1", "kind": "follow_up"},
               {"role": "assistant", "content": "q2", "kind": "follow_up"},
               {"role": "assistant", "content": "A medic can visit.", "kind": "recommendation"}]
    result = run(p, "I also have another concern", history=history)
    assert result.follow_up_question == "What would you like help with now?"


def test_unresolved_danger_sign_does_not_repeat_the_same_screening_question():
    safety = {"findings": [{"flag": "breathlessness", "status": "possible", "evidence": "unclear"}],
              "screening_question": "Is breathing difficult?", "screening_options": ["Yes", "No"]}
    p = make(safety=safety, tri=triage(care_type="paramedic_home_visit"))
    result = run(p, "I cannot tell", history=[{"role": "assistant", "content": "Is breathing difficult?", "kind": "follow_up"}])
    assert result.care_type == "emergency_112" and result.follow_up_question is None
    assert result.matched_caregivers == []


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
