import numpy as np
import pytest

from ccpipe.triage import cv
from ccpipe.triage.data import CLASSES, FOLLOWUP, URGENCY_OF, load_unique
from ccpipe.triage.features import to_roman
from ccpipe.triage.zoo import all_configs, build


@pytest.mark.parametrize("a,b", [("बुखार", "bukhar"), ("खांसी", "khansi"), ("सांस नहीं आ रही", "saans nahi aa rahi"),
                                 ("bukhaar", "bukhar")])
def test_roman_view_bridges_scripts_and_spellings(a, b):
    assert to_roman(a) == to_roman(b)


def test_roman_is_idempotent_on_latin():
    for t in ["fever and cough", "ghar pe injection"]:
        assert to_roman(to_roman(t)) == to_roman(t)


def test_unique_table(cc_csv):
    df = load_unique()
    assert len(df) == 66 and df["rows"].sum() == 340
    assert set(df["label"]) == set(CLASSES)
    assert df.groupby("family")["fold"].nunique().max() == 1  # no family straddles folds


def test_urgency_is_function_of_care_type(cc_csv):
    df = load_unique()
    labelled = df[df["label"] != FOLLOWUP]
    assert labelled.groupby("label")["urgency"].nunique().max() == 1
    for label, urg in labelled.groupby("label")["urgency"].first().items():
        assert URGENCY_OF[label] == urg


def test_every_config_fits_on_text_only_input():
    texts = ["fever and cough", "बुखार और खांसी", "need injection at home", "इंजेक्शन चाहिए", "chest pain", "सीने में दर्द"]
    labels = ["paramedic_home_visit", "paramedic_home_visit", "home_nursing", "home_nursing", "emergency_112", "emergency_112"]
    for fs, clf in all_configs():
        model = build(fs, clf).fit(texts, labels)
        assert model.predict(["fever"]).shape == (1,)


def test_lofo_never_trains_on_the_held_out_family(cc_csv):
    df = load_unique()
    groups = df["family"].to_numpy()
    for train, test in cv.lofo_splits(groups):
        assert not set(groups[train]) & set(groups[test])


def test_score_counts_emergency_misses():
    s = cv.score(["emergency_112", "emergency_112", "home_nursing"], ["home_nursing", "emergency_112", "emergency_112"])
    assert s["emergency_fn"] == 1 and s["over_triage"] == 1


def test_emergency_threshold_arithmetic():
    from ccpipe.triage.emergency import TAU, at_threshold

    y = np.array([1, 1, 0, 0])
    p = np.array([0.40, 0.30, 0.34, 0.10])
    assert TAU == 0.10
    r = at_threshold(y, p, 0.35)
    assert r["tp"] == 1 and r["fn"] == 1 and r["fp"] == 0
    assert at_threshold(y, p, 0.30)["fp"] == 1  # 0.34 >= 0.30
    assert at_threshold(y, p, TAU)["fp"] == 2  # the 0.10 boundary is inclusive


def _synthetic(n_per=6, seed=0):
    import pandas as pd

    rng = np.random.default_rng(seed)
    fams, labels = [], []
    for i, lab in enumerate(CLASSES):
        for k in range(3):
            fams += [f"{lab}{k}"] * (n_per // 3)
            labels += [lab] * (n_per // 3)
    df = pd.DataFrame({"family": fams, "label": labels, "text": [str(i) for i in range(len(labels))]})
    y = np.array([CLASSES.index(l) for l in labels])
    good = np.full((len(y), 6), 0.02); good[np.arange(len(y)), y] = 0.9
    noise = rng.dirichlet(np.ones(6), size=len(y))
    return df, good / good.sum(1, keepdims=True), noise


def test_stacker_prefers_informative_model_and_weights_nonnegative():
    from ccpipe.triage.ensemble import fit_stacker

    df, good, noise = _synthetic()
    y = np.array([CLASSES.index(l) for l in df["label"]])
    w, b = fit_stacker([good, noise], y)
    assert (w >= 0).all() and w[0] > w[1]


def test_stack_lofo_runs_and_emergency_override():
    from ccpipe.triage.ensemble import lofo_stack

    df, good, noise = _synthetic()
    labels, probs, w = lofo_stack(df, [good, noise], tau=0.10)
    assert probs.shape == (len(df), 6) and np.allclose(probs.sum(1), 1)
    assert (labels[probs[:, CLASSES.index("emergency_112")] >= 0.10] == "emergency_112").all()
