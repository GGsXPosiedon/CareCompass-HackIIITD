"""Stateless pathway requests exercise the real graph and wire contract."""
import pytest

from app.services import delhi, pathways
from conftest import req


def ask(client, text, history, **extra):
    response = client.post("/triage", json={**req(text, language="en", history=history, location=None), **extra})
    assert response.status_code == 200
    body = response.json()
    history.extend([{"role": "user", "content": text},
                    {"role": "assistant", "content": body["follow_up_question"] or body["reasoning"]}])
    return body


@pytest.mark.parametrize("answer", ["Yes", "Not sure", "Haan", "पता नहीं"])
def test_pathway_danger_uses_existing_emergency_response(client, answer):
    history = []
    first = ask(client, "I have a fever", history)
    assert pathways.question_slot(first["follow_up_question"]) == "pathway:fever:danger"
    body = ask(client, answer, history)
    assert body["care_type"] == "emergency_112" and body["urgency"] == "emergency"
    assert "112" in body["reasoning"] and body["matched_caregivers"] == []


@pytest.mark.parametrize("context,urgency", [({}, "scheduled"), ({"age_years": 0.5}, "same_day"),
                                          ({"pregnant": True}, "same_day")])
def test_pathway_replays_history_and_converges_in_four_questions(client, context, urgency):
    history = []
    for text in ["I have a fever in govind puri", "No", "No", "Less than 2 days", "Yes"]:
        body = ask(client, text, history, patient_context=context)
    assert body["follow_up_question"] is None
    assert body["urgency"] == urgency and "UNREVIEWED" in body["reasoning"]
    assert len([t for t in history if t["role"] == "assistant" and pathways.question_slot(t["content"])]) == 4


def test_anger_limits_questions_and_offers_callback_without_claiming_booking(client):
    history = []
    first = ask(client, "I have a fever and I am fed up", history)
    assert first["follow_up_question"] and "human call-back" in first["reasoning"]
    body = ask(client, "No", history)
    assert body["follow_up_question"] is None and body["urgency"] == "same_day"
    assert "human call-back" in body["reasoning"]


def test_panic_uncertain_danger_escalates(client):
    history = []
    first = ask(client, "Help me please", history)
    assert "chest pain" in first["follow_up_question"]
    assert ask(client, "Not sure", history)["care_type"] == "emergency_112"


def test_new_topic_and_stop_do_not_continue_pathway(client):
    history = []
    ask(client, "I have a fever", history)
    assert ask(client, "Stop", history)["care_type"] is None
    body = ask(client, "I need a blood test at home", history)
    assert body["care_type"] == "lab_test_home"


def test_new_symptom_starts_a_new_pathway(client):
    history = []
    ask(client, "I have a fever", history)
    body = ask(client, "Actually I have a cough", history)
    assert pathways.question_slot(body["follow_up_question"]) == "pathway:cough_breathing:danger"


def test_unrecognised_answers_converge_conservatively(client):
    history = []
    for text in ["I have a fever", "xyz", "xyz", "xyz", "xyz"]:
        body = ask(client, text, history)
    assert body["care_type"] == "emergency_112"


def test_pathway_runs_without_loading_weights(client, pipeline, monkeypatch):
    import app.main as main
    from app.services.encoder_models import EncoderModels
    from app.services.pipeline import Pipeline

    def forbidden(*args, **kwargs):
        raise AssertionError("Runtime encoder loading is forbidden in rules mode")

    monkeypatch.setattr(EncoderModels, "maybe", forbidden)
    fresh = Pipeline(settings=pipeline.settings, repo=pipeline.repo, matcher=pipeline.matcher, llm=pipeline.llm)
    assert fresh.encoder is None
    monkeypatch.setattr(main, "get_pipeline", lambda: fresh)
    history = []
    ask(client, "I have a fever", history)
    assert ask(client, "No", history)["follow_up_question"]


def test_invalid_patient_context_is_rejected(client):
    for context in [{"age_years": -1}, {"age_years": 200}, {"pregnant": "maybe"}]:
        assert client.post("/triage", json={**req("fever"), "patient_context": context}).status_code == 422


def test_seasonal_emphasis_keeps_question_and_disposition(client):
    history = []
    ask(client, "I have a fever in govind puri", history)
    body = ask(client, "No", history)
    assert pathways.question_slot(body["follow_up_question"]) == "pathway:fever:bleed"
    assert "Seasonal context (UNREVIEWED)" in body["reasoning"]
    assert body["care_type"] is None


def test_llm_safety_can_escalate_a_pathway_question(client, pipeline):
    from app.schemas.llm import SafetyReview

    class SafetyLLM:
        enabled = True

        def structured(self, *args, **kwargs):
            return SafetyReview.model_validate({
                "findings": [{"flag": "breathlessness", "status": "present", "evidence": "danger"}],
                "screening_question": None, "screening_options": [],
            })

    pipeline.llm = SafetyLLM()
    body = ask(client, "I have a fever", [])
    assert body["care_type"] == "emergency_112" and body["red_flags"] == ["breathlessness"]
    assert body["matched_caregivers"] == []


def test_delhi_alias_used_for_matching(client, pipeline, monkeypatch):
    locations = []
    original = pipeline.matcher.match

    def capture(*args):
        locations.append(args[-2])
        return original(*args)

    monkeypatch.setattr(pipeline.matcher, "match", capture)
    ask(client, "Need a blood test at home in govind puri", [])
    assert locations[0].lat == 28.5434 and locations[0].lng == 77.2628
    assert delhi.resolve("greater noida")["name"] == "Greater Noida"
    assert delhi.resolve("gurgaon") is None  # ambiguous aliases must not invent a location
