import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.db.repository import CaregiverRepository  # noqa: E402
from app.services.matching import Matcher  # noqa: E402
from app.services.pipeline import Pipeline  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
LOC = {"lat": 28.54, "lng": 77.27}


@pytest.fixture()
def pipeline():
    s = get_settings()
    repo = CaregiverRepository(s.caregivers_path)
    matcher = Matcher(repo, s, now_fn=lambda: datetime(2026, 10, 24, 12, 0, tzinfo=IST))
    import dataclasses
    s = dataclasses.replace(s, gemini_api_key="")  # deterministic tests never call an LLM
    from app.services.gemini import GeminiClient
    return Pipeline(settings=s, repo=repo, matcher=matcher, llm=GeminiClient(s))


@pytest.fixture()
def client(pipeline, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "get_pipeline", lambda: pipeline)
    return TestClient(main.app)


def req(text, language="auto", history=None, location=LOC):
    d = {"user_input": text, "language": language, "conversation_history": history or []}
    if location:
        d["location"] = location
    return d
