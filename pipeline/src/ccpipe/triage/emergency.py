"""Binary emergency detector with an explicit probability threshold (team setting 0.10, set by the user on 2026-10-24).

Rule: declare emergency when P(emergency | text) >= tau. Evaluated leave-one-family-out, so each held-out
emergency family is a scenario the model has never seen. This is a *learned* signal only; the hard-rule path
(Stage 5) must still run first and can never be cancelled by a low score here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import FeatureUnion, Pipeline

from .data import load_unique
from .zoo import FEATURE_SETS, _branch

TAU = 0.10
SWEEP = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.70, 0.80]
# Declared BEFORE looking at results, to avoid picking the winner on the test folds.
PRIMARY = ("raw_char", 10.0, "balanced")


def build_binary(feature_set: str, C: float, weight) -> Pipeline:
    union = FeatureUnion([(k, _branch(k)) for k in FEATURE_SETS[feature_set]])
    return Pipeline([("features", union), ("clf", LogisticRegression(C=C, class_weight=None if weight == "none" else "balanced", max_iter=3000))])


def lofo_probs(df: pd.DataFrame, feature_set: str, C: float, weight: str) -> np.ndarray:
    y = (df["label"] == "emergency_112").to_numpy().astype(int)
    fam = df["family"].to_numpy()
    p = np.zeros(len(df))
    for g in sorted(set(fam)):
        te = fam == g
        m = build_binary(feature_set, C, weight).fit(df["text"][~te].tolist(), y[~te])
        p[te] = m.predict_proba(df["text"][te].tolist())[:, 1]
    return p


def at_threshold(y: np.ndarray, p: np.ndarray, tau: float) -> dict:
    pred = p >= tau
    tp, fn = int((pred & (y == 1)).sum()), int((~pred & (y == 1)).sum())
    fp = int((pred & (y == 0)).sum())
    return {"tau": tau, "tp": tp, "fn": fn, "fp": fp, "recall": tp / max(tp + fn, 1),
            "precision": tp / max(tp + fp, 1) if tp + fp else float("nan"), "fpr": fp / max(int((y == 0).sum()), 1)}


def recall_ci(df: pd.DataFrame, y: np.ndarray, p: np.ndarray, tau: float, n: int = 2000, seed: int = 0):
    rng = np.random.default_rng(seed)
    fams = sorted(df["family"].unique())
    idx = {f: np.where(df["family"].to_numpy() == f)[0] for f in fams}
    vals = []
    for _ in range(n):
        ii = np.concatenate([idx[f] for f in rng.choice(fams, len(fams))])
        pos = y[ii] == 1
        if pos.sum():
            vals.append(float((p[ii][pos] >= tau).mean()))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def run() -> dict:
    df = load_unique()
    y = (df["label"] == "emergency_112").to_numpy().astype(int)
    rows, probs = [], {}
    for fs in FEATURE_SETS:
        for C in (1.0, 10.0, 100.0):
            for w in ("balanced", "none"):
                p = lofo_probs(df, fs, C, w)
                probs[(fs, C, w)] = p
                r = at_threshold(y, p, TAU)
                rows.append({"features": fs, "C": C, "weight": w, "auroc": roc_auc_score(y, p),
                             "pr_auc": average_precision_score(y, p), "mean_p_emerg": p[y == 1].mean(),
                             "mean_p_other": p[y == 0].mean(), **{k: r[k] for k in ("recall", "fn", "fp")}})
    table = pd.DataFrame(rows)
    pp = probs[PRIMARY]
    sweep = pd.DataFrame([at_threshold(y, pp, t) for t in SWEEP])
    fam_p = (df.assign(p=pp).groupby(["family", "label"])["p"].agg(["min", "mean", "max"]).reset_index())
    return {"df": df, "y": y, "table": table, "sweep": sweep, "fam_p": fam_p, "primary_p": pp,
            "ci": recall_ci(df, y, pp, TAU)}


def _md(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(out)


def write_report() -> dict:
    from ..paths import REPORTS_DIR

    res = run()
    t, sw, ci = res["table"], res["sweep"], res["ci"]
    fs, C, w = PRIMARY
    r35 = sw[sw.tau == TAU].iloc[0]
    L = [f"# 06c — Emergency score threshold (tau = {TAU})", "",
         "Rule under test: declare emergency when P(emergency | text) >= tau. Binary logistic regression, "
         "leave-one-family-out (each held-out emergency family is an unseen scenario), 9 emergency vs 57 other unique texts. "
         f"Primary model fixed in advance: features `{fs}`, C={C:g}, class_weight={w}.", "",
         f"## At tau = {TAU}", "",
         f"Recall {r35.recall:.3f} ({int(r35.tp)}/9 emergencies caught, {int(r35.fn)} missed), false alarms {int(r35.fp)}/57. "
         f"Family-bootstrap 95% interval on recall: {ci[0]:.2f}–{ci[1]:.2f}.", "",
         "## Threshold sweep (primary model)", "", _md(sw), "",
         "Reading it: the score ranks emergencies well (see AUROC below). Lowering tau trades missed emergencies for false alarms: "
         "compare the rows above. "
         "A tau chosen on these same folds is optimistic, and a probability like this has no absolute meaning: it depends "
         "on regularisation and class weighting (rows below), so re-pick tau whenever the model changes.", "",
         "## Score of each emergency family (min / mean / max over its texts)", "",
         _md(res["fam_p"][res["fam_p"].label == "emergency_112"]), "",
         f"## All configurations at tau = {TAU}", "", _md(t.sort_values("auroc", ascending=False)), "",
         "`auroc`/`pr_auc` are threshold-free. `weight=none` shrinks scores and makes high-ish thresholds unreachable; `balanced` inflates them. "
         "Neither is 'calibrated': 66 texts are too few to calibrate probabilities.", "",
         "## Safety note", "",
         "A learned score is never the only emergency path. Stage 5's hard-rule check runs first and cannot be cancelled "
         "by a low score; this detector only adds recall on top of it.", ""]
    (REPORTS_DIR / "06c_emergency_threshold.md").write_text("\n".join(L), encoding="utf-8")
    return {"recall_at_tau": float(r35.recall), "fn": int(r35.fn), "fp": int(r35.fp)}
