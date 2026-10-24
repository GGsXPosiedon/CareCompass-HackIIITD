import numpy as np
import pytest
import yaml

from ccpipe.followup.select import bank, next_question
from ccpipe.paths import PIPELINE_DIR as ROOT
from ccpipe.retrieval.bm25 import BM25
from ccpipe.retrieval.fusion import rrf, softmax_weights
from ccpipe.retrieval.infogain import entropy, information_gain, rank_questions

CASES = yaml.safe_load((ROOT / "eval" / "followup_cases.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("c", CASES, ids=[c["id"] for c in CASES])
def test_followup_cases(c):
    q = next_question([c["text"]], [], c["lang"])
    if c["first"] is None:
        assert q is None
        return
    assert q is not None and q.id == c["first"]
    # walk the whole sequence: no repeats, nothing from `never`, and danger questions never come after routine ones
    asked, seq = [], []
    while (q := next_question([c["text"]], asked, c["lang"])) is not None:
        asked.append(q.id)
        seq.append(q)
    assert len(asked) == len(set(asked))
    assert not set(asked) & set(c.get("never", []))
    flags = [s.danger for s in seq]
    assert flags == sorted(flags, reverse=True)


def test_language_and_options_match():
    for lang in ("en", "hi", "hinglish"):
        q = next_question(["knee pain"], [], lang)
        assert q.text == bank()["symptoms"]["knee_pain"][0][lang]
        assert q.options == bank()["options"][lang]


def test_bank_complete_and_draft():
    assert bank()["review_status"] == "unreviewed"
    for sym, qs in bank()["symptoms"].items():
        ids = [q["id"] for q in qs]
        assert len(ids) == len(set(ids))
        assert any(q.get("danger") for q in qs), sym
        for q in qs:
            assert all(q.get(l) for l in ("en", "hi", "hinglish")) and q["purpose"]


def test_bm25_prefers_matching_doc_and_rrf_fuses():
    docs = ["knee pain and swelling", "fever and cough", "need blood test at home"]
    s = BM25(docs).scores("my knee pain")
    assert int(np.argmax(s)) == 0 and s[1] == 0
    fused = rrf(np.array([3.0, 2.0, 1.0]), np.array([1.0, 3.0, 2.0]))
    assert int(np.argmax(fused)) in (0, 1)
    assert abs(softmax_weights(np.array([0.9, 0.5, 0.1]), 0.05).sum() - 1) < 1e-9


def test_information_gain_extremes():
    labels, w = ["a", "a", "b", "b"], [0.25] * 4
    perfect = [{"y": 1.0}, {"y": 1.0}, {"n": 1.0}, {"n": 1.0}]
    useless = [{"y": 0.5, "n": 0.5}] * 4
    assert abs(information_gain(labels, w, perfect) - 1.0) < 1e-9
    assert abs(information_gain(labels, w, useless)) < 1e-9
    assert abs(entropy({"a": 0.5, "b": 0.5}) - 1.0) < 1e-9
    ranked = rank_questions(labels, w, {"p": perfect, "u": useless}, danger={"u": 1.0}, lam=10.0)
    assert ranked[0][0] == "u"  # a danger question outranks any information gain
