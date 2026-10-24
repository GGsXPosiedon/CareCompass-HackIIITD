from collections import Counter
from datetime import datetime

from app.config import DATA_DIR, Settings
from app.db.repository import CaregiverRepository
from app.schemas.external import Location
from app.services.matching import Matcher
from conftest import IST
from fastapi.testclient import TestClient


def test_supplied_roster_loads_all_unique_caregivers_and_valid_slots():
    repo = CaregiverRepository(str(DATA_DIR / "caregivers.csv"))
    rows = repo.all()
    assert len(rows) == len({row.caregiver_id for row in rows}) == 60
    assert Counter(row.role for row in rows) == {"doctor": 18, "medic": 28, "phlebotomist": 14}
    assert sum(row.active for row in rows) == 52
    matcher = Matcher(repo, Settings(), now_fn=lambda: datetime(2026, 10, 24, 8, 0, tzinfo=IST))
    for row in rows:
        assert -90 <= row.lat <= 90 and -180 <= row.lng <= 180
        assert row.max_radius_km > 0 and 0 <= row.rating <= 5
        assert row.languages and row.skills
        datetime.strptime(row.free_from, "%H:%M")
        datetime.strptime(row.free_until, "%H:%M")
        if row.active:
            assert matcher.slots_for(row, matcher.now().date())


def test_supplied_roster_matching_returns_only_eligible_real_ids():
    repo = CaregiverRepository(str(DATA_DIR / "caregivers.csv"))
    matcher = Matcher(repo, Settings(), now_fn=lambda: datetime(2026, 10, 24, 9, 0, tzinfo=IST))
    for care, skill in [("teleconsultation", "teleconsultation"), ("lab_test_home", "sample_collection")]:
        matches = matcher.match(care, "scheduled", [{skill}], {skill}, "en", Location(lat=28.54, lng=77.27))
        assert matches
        for match in matches:
            caregiver = repo.get(match.caregiver_id)
            assert caregiver and caregiver.caregiver_id.startswith("CG_") and caregiver.active
            assert skill in caregiver.skills


def test_default_api_serves_profiles_from_supplied_roster():
    from app.main import app, get_pipeline

    get_pipeline.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.get('/caregivers', params={"ids": "CG_001,CG_002", "date": "2026-10-25"})
        assert response.status_code == 200
        profiles = response.json()
        assert [(row['id'], row['name']) for row in profiles] == [("CG_001", "Mohit Gupta"), ("CG_002", "Mohit Bisht")]
    finally:
        get_pipeline.cache_clear()
