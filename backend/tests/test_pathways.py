import json
from app.services import mood, pathways as pw


def run(pid, ans_by_q, **kw):
    ans = {}
    for _ in range(10):
        s = pw.evaluate(pid, ans, **kw)
        if s.kind == "disposition":
            return s
        ans[s.question_id] = ans_by_q[s.question_id]
    raise AssertionError("did not converge")


def test_content_is_valid_complete_and_marked_unreviewed():
    d = pw.load()
    assert "UNREVIEWED" in d["status"] and d["max_questions"] == 4
    for p in d["pathways"]:
        assert 2 <= len(p["questions"]) <= 4, p["id"]
        qids = {q["id"] for q in p["questions"]}
        assert any(q["danger"] for q in p["questions"]) and p["cues"]
        for q in p["questions"]:
            assert set(q["text"]) == {"en", "hinglish", "hi"} and all(set(o["label"]) == {"en", "hinglish", "hi"} for o in q["options"])
        for r in p["rules"]:
            assert r["disposition"] in pw.ORDER and r["urgency"] in ("emergency", "same_day", "scheduled") and set(r["why"]) == {"en", "hinglish", "hi"}
            assert set(r["when"]) <= qids
            assert (r["disposition"] == "emergency") == (r["care_type"] == "emergency_112")
            assert (r["disposition"] == "self_care") == ("advice" in r), p["id"]
            if "advice" in r:
                assert set(r["advice"]) == {"en", "hinglish", "hi"}


def test_select_in_three_languages():
    assert pw.select("papa ko bukhar hai") == "fever" and pw.select("मुझे खांसी है") == "cough_breathing"
    assert pw.select("I have chest pain") == "chest_pain" and pw.select("write a poem") is None


def test_danger_answer_or_unsure_is_emergency_immediately():
    for ans in ("yes", "unsure"):
        s = pw.evaluate("fever", {"danger": ans})
        assert s.kind == "disposition" and s.care_type == "emergency_112" and s.asked == 1
    assert pw.evaluate("chest_pain", {"now": "yes"}).care_type == "emergency_112"


def test_converges_within_four_questions_and_explains():
    s = run("fever", {"danger": "no", "bleed": "no", "duration": "short", "fluids": "yes"})
    assert s.disposition == "self_care" and s.advice and s.why and s.asked <= 4 and s.care_type == "teleconsultation"
    assert run("fever", {"danger": "no", "bleed": "yes"}).disposition == "urgent"
    assert run("fever", {"danger": "no", "bleed": "no", "duration": "long", "fluids": "yes"}).urgency == "same_day"


def test_strict_thresholds_infant_pregnant_child_elder():
    calm = {"danger": "no", "bleed": "no", "duration": "short", "fluids": "yes"}
    assert run("fever", calm, age_years=0.5).disposition == "urgent" and run("fever", calm, age_years=0.5).raised_by == "infant"
    assert run("fever", calm, pregnant=True).disposition == "urgent"
    assert run("fever", calm, age_years=3).disposition == "routine" and run("fever", calm, age_years=3).advice is None
    assert run("fever", calm, age_years=70).disposition == "routine"
    assert run("fever", calm, age_years=30).disposition == "self_care"


def test_skip_is_treated_as_unsure_and_never_lowers_a_danger_answer():
    assert pw.evaluate("cough_breathing", {"danger": "skip"}).care_type == "emergency_112"


def test_parse_answer_multilingual():
    assert pw.parse_answer("fever", "danger", "Haan") == "yes" and pw.parse_answer("fever", "danger", "nahi") == "no"
    assert pw.parse_answer("fever", "danger", "pata nahi") == "unsure" and pw.parse_answer("fever", "danger", "हाँ") == "yes"
    assert pw.parse_answer("fever", "duration", "2 to 4 days") == "mid" and pw.parse_answer("fever", "duration", "blah") is None


def test_hindi_output():
    s = pw.evaluate("fever", {}, lang="hi")
    assert s.kind == "question" and "साँस" in s.question


def test_mood_panic_anger_anxiety_neutral():
    assert mood.detect("please help jaldi aao mummy ko kuch ho gaya!!!").label == "panic"
    assert mood.detect("yeh bakwas hai, bilkul bekaar service").human_callback
    m = mood.detect("mujhe bahut dar lag raha hai, is it serious?")
    assert m.label == "anxiety" and not m.danger_first
    assert mood.detect("papa ko do din se bukhar hai").label == "neutral"
    assert mood.detect("help me please").unsure_is_yes


def test_delhi_assets_cover_every_caregiver_area():
    d = json.load(open(pw.RULES.parent / "delhi.json", encoding="utf-8"))
    assert len(d["areas"]) == 18 and d["emergency"]["unified"] == "112" and "UNREVIEWED" in d["status"]
