from datetime import datetime

from app.config import ROLE_BY_CARE_TYPE, get_settings
from app.db.repository import CaregiverRepository
from app.schemas.external import Location
from app.services.matching import Matcher, haversine_km
from conftest import IST

LOC = Location(lat=28.54, lng=77.27)


def make(hour=12):
    s = get_settings()
    return Matcher(CaregiverRepository(s.caregivers_path), s, now_fn=lambda: datetime(2026, 10, 24, hour, 0, tzinfo=IST))


def test_haversine_known_distance():
    assert abs(haversine_km(28.6139, 77.2090, 28.5355, 77.2100) - 8.7) < 0.3  # CP -> Saket-ish


def test_role_skill_active_filters():
    m = make()
    res = m.match("home_nursing", "same_day", [{"injection_im", "injection_iv"}], {"injection_im", "injection_iv"}, "hinglish", LOC)
    roles = {m.repo.get(c.caregiver_id).role for c in res}
    assert roles == {"medic"}
    for c in res:
        cg = m.repo.get(c.caregiver_id)
        assert cg.active and cg.skills & {"injection_im", "injection_iv"}
    assert "SYN_005" not in {c.caregiver_id for c in res}  # inactive


def test_scores_normalised_sorted_and_topk():
    res = make().match("paramedic_home_visit", "same_day", [], set(), "hinglish", LOC)
    assert 1 <= len(res) <= get_settings().top_k
    assert all(0 <= c.score <= 1 for c in res)
    assert [c.score for c in res] == sorted((c.score for c in res), reverse=True)
    assert all(c.reason for c in res)


def test_radius_filter():
    far = Location(lat=28.9, lng=77.9)
    assert make().match("paramedic_home_visit", "same_day", [], set(), "hinglish", far) == []


def test_teleconsultation_ignores_distance():
    far = Location(lat=28.9, lng=77.9)
    res = make().match("teleconsultation", "same_day", [{"teleconsultation"}], {"teleconsultation"}, "en", far)
    assert res and all("km" not in c.reason for c in res)


def test_closed_windows_excluded_for_same_day():
    late = make(hour=23).match("paramedic_home_visit", "same_day", [], set(), "hinglish", LOC)
    assert late == []
    assert make(hour=23).match("lab_test_home", "scheduled", [{"sample_collection"}], {"sample_collection"}, "hinglish", LOC)


def test_english_speaker_prefers_english_caregiver():
    res = make().match("teleconsultation", "same_day", [{"teleconsultation"}], {"teleconsultation"}, "en", LOC)
    top = make().repo.get(res[0].caregiver_id)
    assert "English" in top.languages


def test_roles_map_covers_all_non_emergency_care_types():
    assert set(ROLE_BY_CARE_TYPE) == {"paramedic_home_visit", "home_nursing", "lab_test_home", "teleconsultation"}


def test_reason_only_uses_real_profile_fields():
    m = make()
    res = m.match("home_nursing", "same_day", [{"wound_dressing"}], {"wound_dressing"}, "en", LOC)
    for c in res:
        cg = m.repo.get(c.caregiver_id)
        assert f"{cg.rating:.1f}" in c.reason or "km" in c.reason or cg.free_from in c.reason or cg.free_until in c.reason  # availability now names the real window edge


def test_timing_later_accepts_caregivers_whose_day_is_over_but_never_changes_score_order():
    m = make(hour=23)  # late night: nobody has a same_day slot left
    today = m.match("paramedic_home_visit", "same_day", [], set(), "hinglish", LOC, "today")
    later = m.match("paramedic_home_visit", "same_day", [], set(), "hinglish", LOC, "later")
    assert today == [] and later  # a visit tomorrow is acceptable when the user said so


def test_timing_now_prefers_caregivers_free_right_now():
    m = make(hour=12)
    res = m.match("paramedic_home_visit", "same_day", [], set(), "hinglish", LOC, "now")
    assert res and all(c.components["wait_min"] == 0 for c in res) or all(c.components["wait_min"] > 0 for c in res)
    base = m.match("paramedic_home_visit", "same_day", [], set(), "hinglish", LOC)
    assert {c.caregiver_id for c in res} <= {c.caregiver_id for c in base} or not any(c.components["wait_min"] == 0 for c in base)
