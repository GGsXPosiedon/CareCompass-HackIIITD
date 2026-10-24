import pytest
from conftest import req

CONTRACT_KEYS = {"follow_up_question", "care_type", "urgency", "red_flags", "reasoning", "matched_caregivers"}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_contract_keys_and_alias_routes(client):
    for path in ("/triage", "/api/v1/triage", "/api/v1/route"):
        body = client.post(path, json=req("papa ko do din se bukhar hai aur khansi bhi")).json()
        assert CONTRACT_KEYS <= set(body)
        assert "answer_options" not in body  # only on follow-ups


def test_canonical_example_routes_to_medic_without_followup(client):
    body = client.post("/triage", json=req("papa ko do din se bukhar hai aur khansi bhi", language="hinglish")).json()
    assert body["care_type"] == "paramedic_home_visit"
    assert body["urgency"] == "same_day"
    assert body["follow_up_question"] is None
    assert body["red_flags"] == []
    assert 1 <= len(body["matched_caregivers"]) <= 3


@pytest.mark.parametrize(
    "text,care,urg",
    [
        ("Doctor prescribed an injection, can someone come home", "home_nursing", "same_day"),
        ("Grandmother has a bedsore that needs dressing", "home_nursing", "same_day"),
        ("घर पर इंजेक्शन लगवाना है", "home_nursing", "same_day"),
        ("Need blood sugar test at home tomorrow morning", "lab_test_home", "scheduled"),
        ("cbc aur thyroid test ghar se sample lekar", "lab_test_home", "scheduled"),
        ("Want to talk to a doctor about my reports", "teleconsultation", "same_day"),
        ("Mild acidity and gas since morning, want to consult a doctor", "teleconsultation", "same_day"),
        ("mummy ka bp sugar ghar pe check karwana hai", "paramedic_home_visit", "same_day"),
        ("मुझे अपनी ब्लड रिपोर्ट डॉक्टर को दिखानी है", "teleconsultation", "same_day"),
        ("reports doctor ko dikhani hai", "teleconsultation", "same_day"),
    ],
)
def test_routing_placeholder_cases(client, text, care, urg):
    body = client.post("/triage", json=req(text)).json()
    assert (body["care_type"], body["urgency"]) == (care, urg)


@pytest.mark.parametrize("text", ["doctor chahiye", "help chahiye", "I want to book something for my mother", "डॉक्टर चाहिए"])
def test_vague_input_asks_one_question_with_options(client, text):
    body = client.post("/triage", json=req(text)).json()
    assert body["follow_up_question"]
    assert body["care_type"] is None and body["urgency"] is None
    assert body["matched_caregivers"] == []
    assert len(body["answer_options"]) == 4


def test_followup_language_follows_input(client):
    assert any("ऀ" <= ch <= "ॿ" for ch in client.post("/triage", json=req("डॉक्टर चाहिए")).json()["follow_up_question"])
    assert "Happy to help" in client.post("/triage", json=req("I need help", language="en")).json()["follow_up_question"]


def test_followup_resolves_with_history(client):
    first = client.post("/triage", json=req("doctor chahiye")).json()
    hist = [
        {"role": "user", "content": "doctor chahiye"},
        {"role": "assistant", "content": first["follow_up_question"]},
    ]
    body = client.post("/triage", json=req("mummy ko 2 din se bukhar hai, ghar pe dikhana hai", history=hist)).json()
    assert body["care_type"] == "paramedic_home_visit"
    assert body["follow_up_question"] is None


def test_answer_option_label_resolves(client):
    q = client.post("/triage", json=req("help chahiye", language="en")).json()
    hist = [{"role": "user", "content": "help chahiye"}, {"role": "assistant", "content": q["follow_up_question"]}]
    for option, care in zip(q["answer_options"], ["paramedic_home_visit", "home_nursing", "lab_test_home", "teleconsultation"]):
        assert client.post("/triage", json=req(option, language="en", history=hist)).json()["care_type"] == care


def test_follow_up_cap_falls_back_to_safe_default(client):
    hist = [
        {"role": "user", "content": "help chahiye"}, {"role": "assistant", "content": "q1?"},
        {"role": "user", "content": "kuch"}, {"role": "assistant", "content": "q2?"},
    ]
    body = client.post("/triage", json=req("pata nahi", history=hist)).json()
    assert body["follow_up_question"] is None
    assert body["care_type"] == "paramedic_home_visit"


def test_frontend_prefix_and_history_shape_accepted(client):
    body = client.post("/triage", json=req("A family member: Papa ko do din se bukhar hai aur khansi bhi.", language="hinglish")).json()
    assert body["care_type"] == "paramedic_home_visit"


def test_validation_errors(client):
    assert client.post("/triage", json={"user_input": ""}).status_code == 422
    assert client.post("/triage", json={"user_input": "x", "language": "klingon"}).status_code == 422
    assert client.post("/triage", json={"user_input": "x", "location": {"lat": 999, "lng": 0}}).status_code == 422


def test_no_location_still_works(client):
    body = client.post("/triage", json=req("papa ko do din se bukhar hai ghar pe dikhana hai", location=None)).json()
    assert body["care_type"] == "paramedic_home_visit"


def test_hindi_reasoning_is_hindi(client):
    body = client.post("/triage", json=req("पापा को दो दिन से बुखार और खांसी है")).json()
    assert any("ऀ" <= ch <= "ॿ" for ch in body["reasoning"])


def test_bookings_flow_and_double_booking(client):
    profile = client.get("/caregivers", params={"ids": "SYN_001", "lat": 28.54, "lng": 77.27}).json()[0]
    assert profile["slots"] and profile["distance"] is not None
    slot = profile["slots"][0]
    payload = {"caregiver_id": "SYN_001", "slot": slot, "date": "2026-10-24"}
    ok = client.post("/bookings", json=payload)
    assert ok.status_code == 200 and ok.json()["id"].startswith("BK-")
    assert client.post("/bookings", json=payload).status_code == 409
    assert slot not in client.get("/caregivers", params={"ids": "SYN_001"}).json()[0]["slots"]


def test_booking_rejects_invalid(client):
    assert client.post("/bookings", json={"caregiver_id": "NOPE", "slot": "10:00", "date": "2026-10-24"}).status_code == 404
    assert client.post("/bookings", json={"caregiver_id": "SYN_001", "slot": "03:00", "date": "2026-10-24"}).status_code == 409
    assert client.post("/bookings", json={"caregiver_id": "SYN_005", "slot": "10:00", "date": "2026-10-25"}).status_code == 404  # inactive
    assert client.post("/bookings", json={"caregiver_id": "SYN_001", "slot": "10:00", "date": "2026-10-01"}).status_code == 409  # past


def test_caregivers_echo_requested_care_type_and_reject_mismatch(client):
    ok = client.get("/caregivers", params={"ids": "SYN_001", "care_type": "home_nursing"}).json()[0]
    assert ok["careType"] == "home_nursing"
    assert client.get("/caregivers", params={"ids": "SYN_008", "care_type": "home_nursing"}).status_code == 422


def test_trace_and_graph_endpoints(client):
    t = client.post("/api/v1/triage/trace", json=req("ghar pe blood test karwana hai")).json()
    assert t["response"]["care_type"] == "lab_test_home" and t["trace"][0]["node"] == "intake"
    assert "fuse" in client.get("/api/v1/graph").text
    assert client.get("/health").json()["llm"] == "off"


def test_openapi_documents_contract(client):
    spec = client.get("/openapi.json").json()
    assert "TriageResponse" in spec["components"]["schemas"] and "PatientContext" in spec["components"]["schemas"]
