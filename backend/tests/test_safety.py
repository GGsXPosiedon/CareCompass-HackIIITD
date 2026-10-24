import pytest
from conftest import req

EMERGENCIES = [
    ("papa ko severe chest pain hai saans nahi aa rahi", {"chest_pain", "breathlessness"}),
    ("My father is having severe chest pain and can't breathe", {"chest_pain", "breathlessness"}),
    ("पापा को तेज सीने में दर्द है और सांस नहीं आ रही", {"chest_pain", "breathlessness"}),
    ("He suddenly collapsed and is not responding", {"unconsciousness"}),
    ("wo achanak gir gaye response nahi de rahe", {"unconsciousness"}),
    ("वो अचानक गिर गए और जवाब नहीं दे रहे", {"unconsciousness"}),
    ("Heavy bleeding that won't stop after an accident", {"severe_bleeding"}),
    ("accident ke baad bleeding ruk nahi rahi", {"severe_bleeding"}),
    ("एक्सीडेंट के बाद खून नहीं रुक रहा", {"severe_bleeding"}),
    ("her face is drooping and speech is slurred", {"stroke_symptoms"}),
    ("he is having a seizure", {"seizure"}),
    ("my 3 month old baby has high fever", {"high_fever_infant"}),
    ("shishu ko tez bukhar hai", {"high_fever_infant"}),
    ("I want to end my life", {"suicidal_ideation"}),
    ("vomiting and loose motion since yesterday, can't keep water down", {"severe_dehydration"}),
    ("mummy ko saans lene me dikkat ho rahi hai", {"breathlessness"}),
    # regressions found by eval/run_eval.py (rules-only mode)
    ("dadi ko saans lene me bahut dikkat ho rahi hai", {"breathlessness"}),
    ("papa ka muh tedha ho gaya aur ek haath kaam nahi kar raha", {"stroke_symptoms"}),
    ("मेरे दो महीने के बच्चे को तेज़ बुखार है", {"high_fever_infant"}),
    ("2 week old baby has fever", {"high_fever_infant"}),
]


@pytest.mark.parametrize("text,flags", EMERGENCIES)
def test_red_flags_escalate_without_caregivers(client, text, flags):
    r = client.post("/triage", json=req(text))
    assert r.status_code == 200
    body = r.json()
    assert body["care_type"] == "emergency_112"
    assert body["urgency"] == "emergency"
    assert flags <= set(body["red_flags"])
    assert body["matched_caregivers"] == []
    assert body["follow_up_question"] is None
    assert "112" in body["reasoning"]


@pytest.mark.parametrize(
    "text",
    [
        "no chest pain, just mild fever since morning",
        "papa ko do din se bukhar hai, seene me dard nahi hai",
        "She is breathing normally, only cough",
    ],
)
def test_explicit_negation_does_not_escalate(client, text):
    body = client.post("/triage", json=req(text)).json()
    assert body["care_type"] != "emergency_112"
    assert body["red_flags"] == []


def test_negation_cannot_hide_a_second_red_flag(client):
    body = client.post("/triage", json=req("no chest pain but he cannot breathe")).json()
    assert body["care_type"] == "emergency_112"
    assert "breathlessness" in body["red_flags"]


def test_red_flag_in_followup_answer_escalates(client):
    hist = [
        {"role": "user", "content": "doctor chahiye"},
        {"role": "assistant", "content": "what do you need?"},
    ]
    body = client.post("/triage", json=req("unko seene me tez dard ho raha hai", history=hist)).json()
    assert body["care_type"] == "emergency_112"
    assert body["matched_caregivers"] == []


def test_model_cannot_lower_but_can_raise(pipeline):
    from app.schemas.internal import RouteDecision, SafetyResult

    safety = pipeline.safety
    fired = SafetyResult(True, ["chest_pain"], ["RF-CP-01"], safety.version)
    assert safety.guard(RouteDecision("teleconsultation", 0.99, [], "x"), fired).requires_emergency
    clear = SafetyResult(False, [], [], safety.version)
    assert safety.guard(RouteDecision("emergency_112", 0.6, [], "x"), clear).requires_emergency


def test_model_guard_escalation_has_no_caregivers(pipeline):
    from app.schemas.internal import RouteDecision

    class Alarmist:
        name = "alarmist"

        def predict(self, facts):
            return RouteDecision("emergency_112", 0.7, [], "test")

    pipeline.router = Alarmist()
    from app.schemas.external import TriageRequest

    resp = pipeline.triage(TriageRequest(**req("mummy ko do din se bukhar hai")))
    assert resp.care_type == "emergency_112" and resp.matched_caregivers == []
