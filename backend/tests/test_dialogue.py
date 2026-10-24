"""Context-aware intent + dialogue layer: casual talk, refusals, corrections, stale context, safety and question limits.
Deterministic (LLM off). Emergencies are decided by the red-flag rules BEFORE the dialogue layer is consulted."""
import dataclasses

import pytest

from app.schemas.external import TriageRequest
from app.schemas.internal import FactStatus
from app.services import dialogue
from conftest import req


def chat(client, messages, language="auto"):
    """Replay a conversation: each reply is appended to the history exactly like the real frontend does."""
    history, out = [], []
    for m in messages:
        body = client.post("/triage", json=req(m, language=language, history=list(history))).json()
        out.append(body)
        history.append({"role": "user", "content": m})
        text = body.get("follow_up_question") or body.get("reasoning") or ""
        if text:
            history.append({"role": "assistant", "content": text})
    return out


def analysis(text, history=None):
    return dialogue.analyze(TriageRequest(**req(text, history=history or [])))


# ---------------------------------------------------------------- general conversation ----------------
@pytest.mark.parametrize("text", ["hello", "hlo", "2+2=?", "abba dabba jabba", "i want to watch netflix", "kya haal hai"])
def test_casual_messages_never_start_triage_or_recommend_caregivers(client, text):
    body = client.post("/triage", json=req(text)).json()
    assert body["follow_up_question"] and body["care_type"] is None and body["urgency"] is None
    assert body["matched_caregivers"] == [] and body["red_flags"] == []


def test_casual_turns_do_not_use_up_the_question_budget(client):
    replies = chat(client, ["hello", "abba dabba jabba", "i want to watch netflix", "mujhe bukhar hai"])
    assert replies[-1]["care_type"] is None and "kab se" in replies[-1]["follow_up_question"]  # still asked about the fever


# ---------------------------------------------------------------- adaptive follow-ups -----------------
def test_fever_flow_asks_duration_then_temperature_then_timing_then_routes(client, pipeline):
    pipeline.settings = dataclasses.replace(pipeline.settings, timing_question=True)  # optional: off by default
    r = chat(client, ["mujhe bukhar hai", "2 din se", "101", "Abhi"])
    assert "kab se" in r[0]["follow_up_question"] and r[0]["answer_options"]
    assert "temperature" in r[1]["follow_up_question"].lower() and r[1]["care_type"] is None
    assert "Visit kab chahiye" in r[2]["follow_up_question"] and r[2]["answer_options"][0] == "Abhi" and r[2]["care_type"] is None
    assert r[3]["care_type"] == "paramedic_home_visit" and r[3]["urgency"] == "same_day" and r[3]["follow_up_question"] is None
    assert 1 <= len(r[3]["matched_caregivers"]) <= 3


def test_question_is_about_the_users_symptom(client):
    q = chat(client, ["I have knee pain"])[0]["follow_up_question"]
    assert "knee pain" in q
    q2 = chat(client, ["I have knee pain", "since last week"])[1]["follow_up_question"]
    assert "swelling" in q2  # the 'anything else' question lists symptoms relevant to a knee
    assert "swelling" not in chat(client, ["I have a fever", "since yesterday"])[1]["follow_up_question"]


def test_message_that_already_says_how_long_is_routed_without_questions(client):
    body = client.post("/triage", json=req("papa ko do din se bukhar hai aur khansi bhi", language="hinglish")).json()
    assert body["care_type"] == "paramedic_home_visit" and body["follow_up_question"] is None


def test_explicit_service_request_is_not_interrogated(client):
    body = client.post("/triage", json=req("mujhe ghar pe blood test karwana hai")).json()
    assert body["care_type"] == "lab_test_home"


def test_never_asks_the_same_slot_twice_and_stops_at_the_cap(client):
    r = chat(client, ["mujhe bukhar hai", "pata nahi", "pata nahi"])
    qs = [x["follow_up_question"] for x in r if x["follow_up_question"]]
    assert len(qs) == len(set(qs)) <= 2
    assert r[2]["care_type"] == "paramedic_home_visit"  # budget spent: commit, do not keep asking


def test_adaptive_questions_can_be_switched_off(client, pipeline):
    pipeline.settings = dataclasses.replace(pipeline.settings, adaptive_slot_questions=False)
    body = client.post("/triage", json=req("mujhe bukhar hai")).json()
    assert body["care_type"] == "paramedic_home_visit"


# ---------------------------------------------------------------- refusal, stop, frustration ----------
def test_refusal_is_respected_and_not_mistaken_for_distress(client):
    r = chat(client, ["mujhe bukhar hai", "mujhe medic nhi chaiyeee mujhe koi bhi nhi chaiye mai ekele hi theek hu"])
    assert r[1]["care_type"] is None and r[1]["matched_caregivers"] == []
    assert "112" in r[1]["follow_up_question"] and "book nahi" in r[1]["follow_up_question"]
    assert "ghabrahat" not in r[1]["follow_up_question"]


@pytest.mark.parametrize("text", ["bhaad me jaaaa", "shut up you are useless", "stop", "bas rehne do"])
def test_frustration_and_stop_end_the_push(client, text):
    r = chat(client, ["mujhe bukhar hai", text])
    assert r[1]["care_type"] is None and r[1]["matched_caregivers"] == []


def test_user_can_change_their_mind_after_refusing(client):
    r = chat(client, ["mujhe do din se bukhar hai", "mujhe kuch nahi chahiye", "ok theek hai, book kar do"])
    assert r[1]["care_type"] is None
    assert r[2]["care_type"] == "paramedic_home_visit"


def test_a_new_request_after_refusal_is_handled_fresh(client):
    r = chat(client, ["mujhe kuch nahi chahiye", "mujhe ghar pe injection lagwana hai"])
    assert r[1]["care_type"] == "home_nursing"


# ---------------------------------------------------------------- corrections, negation, stale context --
def test_later_statement_overrides_earlier_one():
    a = analysis("sorry, bukhar nahi hai, sirf khansi hai", [
        {"role": "user", "content": "mujhe bukhar hai"}, {"role": "assistant", "content": "bukhar kab se hai?"}])
    assert a.concepts["fever"] == FactStatus.ABSENT and a.concepts["cough"] == FactStatus.PRESENT
    assert a.correction and a.symptoms == ["cough"]


@pytest.mark.parametrize("text", ["bukhar nahi hai", "no fever", "बुखार नहीं है", "I don't have a fever", "bukhar nhi hai"])
def test_multilingual_negation_is_not_a_symptom(text):
    a = analysis(text)
    assert a.concepts.get("fever") != FactStatus.PRESENT and "fever" not in a.symptoms


def test_old_symptoms_do_not_leak_into_a_new_request(client, pipeline):
    hist = [{"role": "user", "content": "mujhe do din se bukhar hai"},
            {"role": "assistant", "content": "A Medic can assess this at home (you mentioned: fever). If breathing trouble, call 112."}]
    resp, state = pipeline.run(TriageRequest(**req("mujhe ghar pe blood test karwana hai", history=hist)))
    assert resp.care_type == "lab_test_home"
    f = state["facts"]
    assert not f.present("fever") and f.history == []


def test_unrelated_request_in_reply_to_a_question_starts_a_new_topic(pipeline):
    hist = [{"role": "user", "content": "mujhe bukhar hai"}, {"role": "assistant", "content": "bukhar kab se hai?"}]
    resp, state = pipeline.run(TriageRequest(**req("mujhe ghar pe injection lagwana hai", history=hist)))
    assert resp.care_type == "home_nursing"
    assert state["facts"].analysis.new_topic and not state["facts"].present("fever")


def test_continuation_keeps_earlier_context():
    hist = [{"role": "user", "content": "mujhe do din se bukhar hai"}, {"role": "assistant", "content": "Anything else along with it?"}]
    a = analysis("aur khansi bhi hai", hist)
    assert a.concepts["fever"] == FactStatus.PRESENT and a.concepts["cough"] == FactStatus.PRESENT and not a.new_topic


# ---------------------------------------------------------------- safety is never suppressed -----------
@pytest.mark.parametrize("text", [
    "hello, kal movie dekhi. papa ko seene me tez dard ho raha hai",
    "bhaad me jaa, mere papa ko seene me tez dard hai",
    "mujhe kuch nahi chahiye lekin meri saans nahi aa rahi",
    "I am fine, stop. my father has crushing chest pain",
])
def test_emergency_signal_beats_casual_refusal_and_frustration(client, text):
    body = client.post("/triage", json=req(text)).json()
    assert body["care_type"] == "emergency_112" and body["red_flags"] and body["matched_caregivers"] == []


def test_earlier_emergency_signal_still_counts_after_small_talk(client):
    hist = [{"role": "user", "content": "papa ko seene me tez dard hai"}, {"role": "assistant", "content": "Call 112."}]
    body = client.post("/triage", json=req("thanks, hello", history=hist)).json()
    assert body["care_type"] == "emergency_112"  # the rules read the whole user text; scoping never weakens them


def test_negated_emergency_wording_is_not_an_emergency(client):
    body = client.post("/triage", json=req("no chest pain, hello")).json()
    assert body["care_type"] is None and body["red_flags"] == []


# ---------------------------------------------------------------- question counting --------------------
def test_only_real_questions_count():
    assert not dialogue.is_real_question("Hello! Tell me what is troubling you or someone in your family, and I will help find the right care.")
    assert not dialogue.is_real_question("A Medic can assess this at home. If breathing trouble starts, call 112.")
    assert not dialogue.is_real_question("")
    assert not dialogue.is_real_question("Hello! How can I help you or your family with home care today?")
    assert dialogue.is_real_question("Happy to help. What kind of care do you need?")
    assert dialogue.is_real_question("Is the baby younger than 3 months?")
    assert dialogue.is_real_question("bukhar kab se hai?")


def test_assistant_statements_do_not_consume_the_budget(client):
    hist = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "Hello! How can I help you or your family with home care today?"},
            {"role": "user", "content": "xyz"}, {"role": "assistant", "content": "I didn't quite understand that."}]
    a = analysis("mujhe bukhar hai", hist)
    assert a.questions_asked == 0


def test_slot_templates_are_recognised_in_every_language():
    for lang in ("en", "hi", "hinglish"):
        for slot, q in dialogue.QUESTIONS.items():
            text = q[lang].format(symptom="x", hints="y")
            assert dialogue.slot_of(text) == slot and dialogue.is_real_question(text)


# ---------------------------------------------------------------- contract and trace --------------------
def test_dialogue_replies_respect_the_wire_contract(client):
    for text in ["hello", "mujhe medic nhi chahiye", "mujhe bukhar hai"]:
        body = client.post("/triage", json=req(text)).json()
        assert set(body) >= {"follow_up_question", "care_type", "urgency", "red_flags", "reasoning", "matched_caregivers"}
        assert not (body["follow_up_question"] and body["care_type"])


def test_trace_shows_the_intent_decision(client):
    t = client.post("/triage/trace", json=req("hello")).json()
    nodes = [x["node"] for x in t["trace"]]
    assert nodes == ["intake", "rules_safety", "converse", "llm_safety", "dialogue_reply"]  # llm_safety = reply guard
    assert "intent=greeting" in next(x["detail"] for x in t["trace"] if x["node"] == "converse")


def test_user_can_resume_after_frustration_or_stop(client):
    r = chat(client, ["mujhe do din se bukhar hai", "bhaad me jaaaa", "sorry, ok theek hai book kar do"])
    assert r[1]["care_type"] is None and r[2]["care_type"] == "paramedic_home_visit"


# ---- emergency regression: life-threat wording must never be treated as chit-chat -------------
import pytest
from app.schemas.external import TriageRequest


def _run(client_msgs):
    from app.main import app
    from fastapi.testclient import TestClient
    c = TestClient(app)
    msgs = [{"role": "user", "content": m} for m in client_msgs]
    return c


@pytest.mark.parametrize("text", [
    "my friend is not breathing", "he is not breathing", "what should i do he is not breathing", "she stopped breathing",
    "he is choking", "can't get air", "uski saans band ho gayi", "dad is unconscious", "he won't wake up", "pressure in my chest",
    "dil me dard hai", "bleeding heavily", "vomiting blood", "he can't move his arm", "mouth tedha ho gaya", "foaming at mouth",
    "i want to end my life", "no urine since yesterday and sunken eyes",
])
def test_life_threat_phrasings_fire_rules(text):
    from types import SimpleNamespace as N
    from app.services.safety import SafetyEngine
    from app.services.dialogue import _n
    r = SafetyEngine().evaluate(N(text_norm=_n(text), safety_text_norm=_n(text)))
    assert r.requires_emergency, text


@pytest.mark.parametrize("text", ["my friend is not breathing", "he is bleeding and unconscious", "uska dil ruk gaya hai", "someone collapsed near me"])
def test_urgent_words_are_never_general_chat(text):
    from app.services.dialogue import classify_turn
    from app.services.dialogue import extract_concepts, _n
    c, _ = extract_concepts(_n(text))
    assert classify_turn(text, False, c)[0] not in ("general", "greeting")


def test_screenshot_chat_returns_112(client):
    for msg in ("my friend is not breathing", "he is not breathing", "what should i do he is not breathing"):
        r = client.post("/triage", json=req(msg)).json()
        assert r["care_type"] == "emergency_112" and "breathlessness" in r["red_flags"] and not r["matched_caregivers"], msg


def test_nosebleed_asks_severity_then_escalates_only_if_heavy(client):
    q = client.post("/triage", json=req("mere dost ki naak se khoon arha h")).json()
    assert q["care_type"] is None and "khoon" in q["follow_up_question"].lower()
    hist = [{"role": "user", "content": "mere dost ki naak se khoon arha h"}, {"role": "assistant", "content": q["follow_up_question"]}]
    heavy = client.post("/triage", json=req("abhi bhi bahut tez hai", history=hist)).json()
    assert heavy["care_type"] == "emergency_112" and "severe_bleeding" in heavy["red_flags"]
    calm = client.post("/triage", json=req("ruk gaya", history=hist)).json()
    assert calm["care_type"] != "emergency_112"


def test_semantic_net_catches_unlisted_wording_and_only_raises(client):
    for msg in ("dad is lying on the floor not responding", "uski saans nahi aa rahi aur lips neele ho gaye"):
        assert client.post("/triage", json=req(msg)).json()["care_type"] == "emergency_112", msg
    for msg in ("papa ko bukhar hai", "pata nahi", "i want to watch netflix", "mujhe sir dard hai"):
        assert client.post("/triage", json=req(msg)).json()["care_type"] != "emergency_112", msg


def test_failure_log_records_generic_replies(client, tmp_path, monkeypatch):
    from app.services import failure_log
    monkeypatch.setattr(failure_log, "PATH", tmp_path / "f.jsonl")
    client.post("/triage", json=req("abba dabba jabba"))
    assert "general_reply" in (tmp_path / "f.jsonl").read_text(encoding="utf-8")


def test_hinglish_chat_keeps_language_and_context(client):
    hist, qs = [], []
    for m in ("thak gaya hu", "kal se", "ulti bhi hai shayad"):
        r = client.post("/triage", json=req(m, history=list(hist))).json()
        q = r["follow_up_question"]
        qs.append(q or r["reasoning"])
        hist += [{"role": "user", "content": m}] + ([{"role": "assistant", "content": q}] if q else [])
    assert "kab se" in qs[0] and "kuch aur" in qs[1]          # fatigue is health, Hinglish stays Hinglish, no repeated duration
    assert "How long" not in " ".join(qs) and "kab se" not in qs[2]


def test_timing_is_inferred_not_asked_by_default(client):
    r = chat(client, ["mujhe bukhar hai", "2 din se", "101"])
    assert r[2]["care_type"] == "paramedic_home_visit" and r[2]["follow_up_question"] is None
    t = client.post("/triage/trace", json=req("mujhe bahut tez bukhar hai, 2 din se")).json()["trace"]
    assert any("availability=now (severity)" in x["detail"] for x in t if x["node"] == "match")
    t = client.post("/triage/trace", json=req("mujhe 2 din se bukhar hai")).json()["trace"]
    assert any("availability=today (default)" in x["detail"] for x in t if x["node"] == "match")


def test_timing_never_changes_the_organiser_labels(client, pipeline):
    pipeline.settings = dataclasses.replace(pipeline.settings, timing_question=True)
    for answer in ("Abhi", "Aaj baad mein", "Kal / schedule"):
        r = chat(client, ["mujhe bukhar hai", "2 din se", "101", answer])[3]
        assert (r["care_type"], r["urgency"]) == ("paramedic_home_visit", "same_day"), answer


def test_timing_stated_up_front_is_not_asked_again(client):
    r = chat(client, ["mujhe abhi bukhar hai"])
    assert r[0]["care_type"] == "paramedic_home_visit" and r[0]["follow_up_question"] is None


def test_headache_chat_is_not_an_emergency(client):
    r = chat(client, ["sar me dard hora hai", "1–2 din se"])
    assert r[1]["care_type"] != "emergency_112" and not r[1]["red_flags"]


def test_semantic_net_is_deterministic_across_processes():
    import subprocess, sys
    code = ("from app.services.semantic_safety import SemanticSafety;"
            "print(SemanticSafety().check('sar me dard hora hai 1 2 din se'), SemanticSafety().check('uski saans nahi aa rahi'))")
    outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**__import__("os").environ, "PYTHONHASHSEED": str(s)}).stdout
            for s in (1, 7, 23, 42)}
    assert len(outs) == 1, outs  # was hash()-seeded: same text escalated in some processes only


def test_mild_wording_does_not_make_it_urgent(client):
    t = client.post("/triage/trace", json=req("mujhe halka bukhar hai, 2 din se")).json()["trace"]
    assert any("availability=today (default)" in x["detail"] for x in t if x["node"] == "match")


def test_reasoning_names_the_real_symptoms_and_a_symptom_specific_safety_line(client):
    r = chat(client, ["sar me dard hai", "1–2 din se", "dhundhla"])[2]
    assert "sir dard" in r["reasoning"] and "dhundhla" in r["reasoning"] and "Saans mein taklif" not in r["reasoning"]
    assert "warning sign" in r["reasoning"] and r["care_type"] != "emergency_112"
    k = chat(client, ["knee pain", "a week", "swelling"])[2]
    assert "knee pain" in k["reasoning"] and "swelling" in k["reasoning"]
