import dataclasses
import json

import httpx
import pytest

from app.config import get_settings
from app.schemas.llm import SafetyReview
from app.services.gemini import GeminiClient, LLMError
from app.services.llm_router import LLMRouter, OpenAICompatClient, build_llm

GOOD = {"findings": [], "screening_question": None}


def gemini(status: int, key="k1"):
    def handler(request: httpx.Request) -> httpx.Response:
        if status != 200:
            return httpx.Response(status, json={"error": "x"}, headers={"retry-after": "0"})
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(GOOD)}]}}]})
    s = dataclasses.replace(get_settings(), gemini_api_key=key, llm_backend="auto")
    return GeminiClient(s, transport=httpx.MockTransport(handler))


def compat(status: int, content=None, name="groq"):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        if status != 200:
            return httpx.Response(status, json={"error": "x"}, headers={"retry-after": "0"})
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": content or json.dumps(GOOD)}}]})
    s = dataclasses.replace(get_settings(), llm_backend="auto")
    c = OpenAICompatClient(name, "key", "https://example.test/v1", "m1", s, transport=httpx.MockTransport(handler))
    c.calls = calls
    return c


def test_falls_back_when_primary_is_rate_limited():
    g, q = gemini(429), compat(200)
    router = LLMRouter({"gemini": g, "groq": q}, {"safety": ["gemini", "groq"], "triage": ["groq", "gemini"]})
    assert router.for_role("safety").structured("sys", "hello", SafetyReview).findings == []
    assert q.calls and q.calls[0]["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in q.calls[0]["messages"][0]["content"]


def test_error_reasons_list_every_provider_and_are_body_free():
    router = LLMRouter({"gemini": gemini(429), "groq": compat(401)}, {"safety": ["gemini", "groq"]})
    with pytest.raises(LLMError) as e:
        router.for_role("safety").structured("sys", "hello", SafetyReview)
    assert str(e.value) == "gemini: HTTP 429; groq: HTTP 401"


def test_a_dead_provider_is_skipped_during_cooldown():
    q = compat(200)
    router = LLMRouter({"gemini": gemini(401), "groq": q}, {"safety": ["gemini", "groq"]})
    role = router.for_role("safety")
    role.structured("sys", "one", SafetyReview)
    role.structured("sys", "two", SafetyReview)
    assert len(q.calls) == 2 and "gemini" in router._cool  # second call went straight to groq


def test_bad_json_or_schema_violation_is_an_error_not_a_crash():
    router = LLMRouter({"groq": compat(200, content="not json")}, {"safety": ["groq"]})
    with pytest.raises(LLMError):
        router.for_role("safety").structured("sys", "hello", SafetyReview)
    router = LLMRouter({"groq": compat(200, content=json.dumps({"findings": [], "extra": 1}))}, {"safety": ["groq"]})
    with pytest.raises(LLMError):
        router.for_role("safety").structured("sys", "hello", SafetyReview)


def test_two_providers_split_the_two_decisions_by_default(monkeypatch):
    s = dataclasses.replace(get_settings(), llm_backend="auto", gemini_api_key="a", gemini_api_key_2="b", groq_api_key="", compat_api_key="",
                            llm_safety_chain="", llm_triage_chain="")
    r = build_llm(s)
    assert r.chains["safety"] == ["gemini", "gemini2"] and r.chains["triage"] == ["gemini2", "gemini"]
    s = dataclasses.replace(s, llm_safety_chain="gemini", llm_triage_chain="groq,gemini", groq_api_key="g")
    r = build_llm(s)
    assert r.chains == {"safety": ["gemini"], "triage": ["groq", "gemini"]}


def test_single_provider_and_off_behave_like_before():
    s = dataclasses.replace(get_settings(), llm_backend="auto", gemini_api_key="a", gemini_api_key_2="", groq_api_key="", compat_api_key="",
                            llm_safety_chain="", llm_triage_chain="")
    r = build_llm(s)
    assert r.enabled and r.chains == {"safety": ["gemini"], "triage": ["gemini"]}
    assert not build_llm(dataclasses.replace(s, llm_backend="off")).enabled
    assert not build_llm(dataclasses.replace(s, gemini_api_key="")).enabled


def test_llm_off_is_logged_and_shows_in_health(tmp_path, monkeypatch):
    from app.services import failure_log
    from app.services.pipeline import Pipeline
    from app.schemas.external import TriageRequest
    monkeypatch.setattr(failure_log, "PATH", tmp_path / "f.jsonl")
    monkeypatch.delenv("FAILURE_LOG", raising=False)
    off = LLMRouter({}, {"safety": [], "triage": []})
    resp, state = Pipeline(llm=off).run(TriageRequest(user_input="stomachache"))
    assert resp.service_notice is None  # intentionally disabled providers are not a request failure
    row = json.loads((tmp_path / "f.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert "llm_off" in row["why"] and any("skipped" in e for e in row["llm_errors"])  # still visible in diagnostics
