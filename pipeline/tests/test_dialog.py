import pytest
import yaml

from ccpipe.dialog.policy import decide
from ccpipe.dialog.slots import slot_of_assistant
from ccpipe.dialog.turns import cfg, classify, collapse
from ccpipe.paths import PIPELINE_DIR

CASES = yaml.safe_load((PIPELINE_DIR / "eval" / "dialog_cases.yaml").read_text(encoding="utf-8"))


def replay(turns):
    history, out = [], []
    for t in turns:
        d = decide(history, t[0])
        out.append(d)
        history.append({"role": "user", "content": t[0]})
        if d.message:
            history.append({"role": "assistant", "content": d.message})
    return out


@pytest.mark.parametrize("c", CASES, ids=[c["id"] for c in CASES])
def test_dialog_cases(c):
    decisions = replay(c["turns"])
    for t, d in zip(c["turns"], decisions):
        assert d.action == t[1], (t[0], d.action, d.reason)
        if len(t) > 2:
            assert d.slot == t[2], (t[0], d.slot)
        if len(t) > 3 and d.message:
            from ccpipe.dialog.turns import detect_language

            assert detect_language(d.message) == t[3] or t[3] == "hinglish"
    asks = [d.slot for d in decisions if d.action == "ask"]
    assert len(asks) == len(set(asks)) and len(asks) <= cfg()["max_questions"]


def test_redirects_never_use_budget():
    h = []
    for u in ["hello", "asdf", "netflix chahiye"]:
        d = decide(h, u)
        assert not d.counts_toward_budget
        h += [{"role": "user", "content": u}, {"role": "assistant", "content": d.message}]
    d = decide(h, "mujhe bukhar hai")
    assert d.action == "ask"  # full budget still available after off-topic turns


def test_decline_and_abuse_never_commit_or_ask():
    for text in ["nahi chahiye koi doctor", "shut up you are useless", "bhaad me jaa"]:
        d = decide([{"role": "user", "content": "mujhe bukhar hai"}], text)
        assert d.action in ("acknowledge_decline", "deescalate") and d.slot is None


def test_crisis_beats_everything():
    d = decide([], "bukhar hai aur mai marna chahta hoon")
    assert d.action == "crisis_safety"


def test_collapse_and_recognise_own_questions():
    assert collapse("chaiyeee jaaaa") == "chaiye ja"
    from ccpipe.dialog.slots import render

    for slot in ("duration", "temperature", "severity_pain", "severity", "associated", "patient"):
        for lang in ("en", "hi", "hinglish"):
            assert slot_of_assistant(render(slot, "fever", lang)[0]) == slot


def test_no_slot_template_maps_to_a_care_type():
    # policy must never carry routing: no care-type vocabulary anywhere in the dialog config
    text = (PIPELINE_DIR / "configs" / "dialog.yaml").read_text(encoding="utf-8")
    for bad in ("home_nursing", "paramedic_home_visit", "lab_test_home", "teleconsultation", "emergency_112"):
        assert bad not in text
