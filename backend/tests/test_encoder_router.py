"""Trained e5 heads: wiring tests with a fake encoder (always run) and real-model tests (run when ENCODER_PATH is set)."""
import dataclasses
import json
import os
import time
from pathlib import Path

import numpy as np
import pytest

from app.config import get_settings
from app.schemas.external import TriageRequest
from app.services.encoder_models import ARTIFACT, EncoderModels
from app.services.llm_router import LLMRouter
from app.services.pipeline import Pipeline
from app.services.routing import TrainedRouter

OFF = LLMRouter({}, {"safety": [], "triage": []})


class FakeEmbedder:
    """Deterministic 4-d 'embedding': counts a few keywords, so heads can be exercised without onnxruntime."""
    WORDS = ("pasina", "qwx", "zvy", "kuch")

    def encode(self, texts):
        return np.array([[float(t.lower().count(w)) for w in self.WORDS] for t in texts], dtype="float32")


def fake_models(tau_ask=0.5, tau_em=0.99):
    art = {"version": "test", "classes": ["ask_followup", "home_nursing", "lab_test_home"],
           "coef": [[0, 0, 0, 1.0], [0, 3.0, 0, 0], [0, 0, 3.0, 0]], "intercept": [0.0, 0.0, 0.0],
           "emergency": {"mean": [0, 0, 0, 0], "scale": [1, 1, 1, 1], "coef": [4.0, 0, 0, 0], "intercept": -2.0},
           "tau_ask": tau_ask, "tau_emergency": tau_em}
    m = EncoderModels(FakeEmbedder(), art)
    m.tau_ask, m.tau_emergency, m.tau_margin = tau_ask, tau_em, 0.05  # .env may set EMERGENCY_TAU_*; tests must not depend on it
    return m


def pipe_with(models):
    p = Pipeline(llm=OFF, router=TrainedRouter(models))
    p.encoder = models
    return p


def say(p, *turns):
    hist, r = [], None
    for t in turns:
        r = p.triage(TriageRequest(user_input=t, conversation_history=hist))
        hist += [{"role": "user", "content": t}, {"role": "assistant", "content": r.follow_up_question or r.reasoning}]
    return r


def test_emergency_score_math():
    m = fake_models()
    assert m.scores("pasina pasina").emergency > 0.8 > 0.2 > m.scores("hello").emergency


def test_grey_zone_asks_one_danger_question_then_yes_is_112():
    p = pipe_with(fake_models())
    q = say(p, "mummy ko bukhar hai aur pasina aa raha hai")
    assert q.answer_options == ["Haan, abhi", "Nahi"]
    r = say(p, "mummy ko bukhar hai aur pasina aa raha hai", q.answer_options[0])
    assert r.care_type == "emergency_112" and r.urgency == "emergency" and not r.matched_caregivers


def test_denying_the_danger_signs_is_respected():
    p = pipe_with(fake_models())
    r = say(p, "pasina aa raha hai lekin seene me dard nahi hai, saans theek hai")
    assert not (r.follow_up_question and "chest pain" in r.follow_up_question.lower() or "seene mein dard" in (r.follow_up_question or ""))


def test_very_high_score_goes_to_112_without_a_question():
    p = pipe_with(fake_models(tau_ask=0.3, tau_em=0.9))
    r = say(p, "papa ko bukhar hai pasina pasina pasina")
    assert r.care_type == "emergency_112"


def test_rules_stay_in_front():
    p = pipe_with(fake_models())
    assert say(p, "Doctor prescribed an injection, can someone come home").care_type == "home_nursing"
    assert say(p, "I have chest pain and cannot breathe").care_type == "emergency_112"


def test_artifact_is_complete():
    a = json.loads(Path(ARTIFACT).read_text())
    assert {"classes", "coef", "intercept", "emergency", "tau_ask", "tau_emergency", "lofo"} <= set(a)
    assert 0 < a["tau_ask"] < a["tau_emergency"] <= 1 and len(a["coef"][0]) == len(a["emergency"]["coef"]) == 768


REAL = os.getenv("ENCODER_PATH", "")


@pytest.mark.skipif(not REAL or not Path(REAL).exists(), reason="set ENCODER_PATH to the multilingual-e5-base folder")
def test_real_encoder_pipeline():
    s = dataclasses.replace(get_settings(), router_backend="trained", encoder_path=REAL)
    p = Pipeline(llm=OFF, settings=s, router=None)
    assert p.encoder is not None
    t0 = time.perf_counter()
    r = say(p, "papa ko do din se bukhar hai aur khansi bhi")
    assert r.care_type == "paramedic_home_visit"
    assert (time.perf_counter() - t0) < 2.0
    assert say(p, "Doctor prescribed an injection, can someone come home").care_type == "home_nursing"
    assert say(p, "baby ko 104 bukhar hai 3 mahine ka").care_type == "emergency_112"


class StubRouter:
    """Stands in for TrainedRouter: an encoder decision with a given margin (the fuse step is what is under test)."""
    name = "stub"

    def __init__(self, models, margin, top="home_nursing", runner="lab_test_home"):
        self.models, self.margin, self.top, self.runner = models, margin, top, runner

    def predict(self, facts):
        from app.schemas.internal import RouteDecision
        return RouteDecision(self.top, 0.3, ["stub"], "encoder", emergency_score=0.0, runner_up=self.runner, margin=self.margin)


def stub_pipe(margin, **kw):
    m = fake_models()
    p = Pipeline(llm=OFF, router=StubRouter(m, margin, **kw))
    p.encoder = m
    return p


def test_tied_care_types_get_one_two_option_question_and_the_answer_routes():
    p = stub_pipe(0.01)
    q = say(p, "papa ko 2 din se bukhar hai")
    assert q.answer_options and len(q.answer_options) == 2 and q.care_type is None, q
    assert "nurse" in q.answer_options[0].lower() or "injection" in q.answer_options[0].lower()
    # the question is asked once: the next turn routes with the head's top choice
    r = say(p, "papa ko 2 din se bukhar hai", q.answer_options[0])
    assert r.care_type and not (r.answer_options and len(r.answer_options) == 2)


def test_confident_head_or_pair_without_wording_does_not_ask():
    req = TriageRequest(user_input="papa ko 2 din se bukhar hai", conversation_history=[])
    assert not stub_pipe(0.5).triage(req).answer_options
    assert not stub_pipe(0.01, runner="ask_followup").triage(req).answer_options


def test_trained_router_reports_runner_up_and_margin():
    from app.services.intake import build_facts
    r = TrainedRouter(fake_models()).predict(build_facts(TriageRequest(user_input="qwx zvy", conversation_history=[])))
    assert {r.care_type, r.runner_up} == {"home_nursing", "lab_test_home"} and r.margin is not None and r.margin < 0.01
    r2 = TrainedRouter(fake_models()).predict(build_facts(TriageRequest(user_input="qwx qwx qwx", conversation_history=[])))
    assert r2.care_type == "home_nursing" and r2.margin > 1


class YesLLM:
    enabled = True

    def __init__(self, health, confidence="high"):
        self.health, self.confidence, self.calls = health, confidence, 0

    def structured(self, system, user_text, schema, max_tokens=900):
        from app.schemas.llm import IntentCheck
        if schema is IntentCheck:
            self.calls += 1
            return IntentCheck(health_request=self.health, confidence=self.confidence)
        from app.services.gemini import LLMError
        raise LLMError("only the intent check is stubbed")


def test_llm_intent_fallback_widens_general_to_health_but_never_the_reverse():
    msg = "zxqv ratnamla ke liye kuch sujhao"          # nothing in the lexicon matches
    off = Pipeline(llm=OFF).triage(TriageRequest(user_input=msg, conversation_history=[]))
    assert off.care_type is None and "health" in (off.follow_up_question or "").lower() or off.follow_up_question
    yes = YesLLM(True)
    r = Pipeline(llm=yes).triage(TriageRequest(user_input=msg, conversation_history=[]))
    assert yes.calls >= 1 and r.follow_up_question != off.follow_up_question
    no = YesLLM(False)
    assert Pipeline(llm=no).triage(TriageRequest(user_input=msg, conversation_history=[])).follow_up_question == off.follow_up_question
    unsure = YesLLM(True, "low")
    assert Pipeline(llm=unsure).triage(TriageRequest(user_input=msg, conversation_history=[])).follow_up_question == off.follow_up_question


def test_llm_intent_fallback_skips_everyday_tasks():
    llm = YesLLM(True)
    Pipeline(llm=llm).triage(TriageRequest(user_input="write a python script for my homework", conversation_history=[]))
    assert llm.calls == 0
