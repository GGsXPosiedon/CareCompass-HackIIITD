"""Stage 6 driver: plain LOFO for every config, nested LOFO for the honest estimate, extras, report."""
from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pandas as pd

import time

from ..paths import PIPELINE_DIR, PROCESSED_DIR, REPORTS_DIR
from . import cv
from .data import CLASSES, URGENCY_OF, load_unique
from .zoo import all_configs


def _confusion(y, p) -> pd.DataFrame:
    return pd.crosstab(pd.Categorical(y, CLASSES), pd.Categorical(p, CLASSES), dropna=False,
                       rownames=["true"], colnames=["pred"])


def _md(df: pd.DataFrame, index=True) -> str:
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in d.itertuples(index=False):
        lines.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in row) + " |")
    return "\n".join(lines)


CACHE_DIR = PIPELINE_DIR / "data" / "interim" / "triage_pair_cache"


def warm_cache(budget_s: float) -> bool:
    """Fit missing models for every config until the time budget is spent. True when everything is cached."""
    df = load_unique()
    deadline = time.time() + budget_s
    for fs, clf in all_configs():
        if cv.pair_predictions(df, fs, clf, CACHE_DIR, deadline) is None:
            return False
    return True


def run() -> dict:
    df = load_unique()
    y = df["label"].tolist()
    groups = df["family"].to_numpy()
    out: dict = {"n_unique_texts": len(df), "n_rows": int(df["rows"].sum()), "n_families": df["family"].nunique()}

    maj = Counter(y).most_common(1)[0][0]
    out["majority_baseline"] = cv.score(y, [maj] * len(y))

    plain = []
    for fs, clf in all_configs():
        pred = cv.plain_lofo_from_cache(df, cv.pair_predictions(df, fs, clf, CACHE_DIR))
        plain.append({"features": fs, "clf": clf, **cv.score(y, pred.tolist())})
    plain_df = pd.DataFrame(plain).sort_values(["emergency_recall", "macro_f1"], ascending=False)
    out["plain"] = plain

    pred, chosen = cv.nested_from_cache(df, all_configs(), CACHE_DIR)
    out["nested"] = cv.score(y, pred.tolist())
    out["nested_ci"] = cv.cluster_bootstrap(df, pred)
    out["nested_choice_counts"] = Counter(f"{f}|{c}" for f, c in chosen)
    mode_fs, mode_clf = Counter(chosen).most_common(1)[0][0]
    out["modal_config"] = [mode_fs, mode_clf]

    # text-only nested (no concept features), the figure that is not contaminated by registry authorship
    text_configs = [(f, c) for f, c in all_configs() if "concepts" not in f]
    pred_t, chosen_t = cv.nested_from_cache(df, text_configs, CACHE_DIR)
    out["nested_text_only"] = cv.score(y, pred_t.tolist())
    out["nested_text_only_ci"] = cv.cluster_bootstrap(df, pred_t)
    out["nested_text_only_choice_counts"] = Counter(f"{f}|{c}" for f, c in chosen_t)

    rep = cv.repeated_grouped_cv(df, mode_fs, mode_clf)
    out["repeated_grouped"] = {k: [r[k] for r in rep] for k in rep[0]}

    # approved 3 folds
    folds = []
    for f in sorted(df["fold"].unique()):
        te = np.where(df["fold"].to_numpy() == f)[0]
        tr = np.where(df["fold"].to_numpy() != f)[0]
        p = cv.predict_groups(df, mode_fs, mode_clf, [(tr, te)])[te]
        folds.append({"fold": f, **cv.score(df["label"].iloc[te].tolist(), p.tolist())})
    out["approved_folds"] = folds

    df["pred"] = pred
    df["pred_text_only"] = pred_t
    df["ok"] = df["pred"] == df["label"]
    out["per_family"] = df.groupby("family").agg(label=("label", "first"), n=("ok", "size"), correct=("ok", "sum")).reset_index().to_dict("records")
    out["per_language"] = df.groupby("language")["ok"].mean().to_dict()
    out["latency_ms"] = cv.latency_ms(mode_fs, mode_clf, df)

    # urgency: derived deterministically from predicted care type (pair rules); direct urgency agreement
    der = [URGENCY_OF.get(p) for p in pred]
    true_u = [URGENCY_OF.get(t) for t in y]
    out["urgency_derived_exact"] = float(np.mean([a == b for a, b in zip(der, true_u)]))
    out["care_type_to_urgency_is_function"] = bool(
        df[df.label != "ask_followup"].groupby("label")["urgency"].nunique().max() == 1)

    df.to_csv(PROCESSED_DIR / "triage_lofo_predictions.csv", index=False, encoding="utf-8")
    (PROCESSED_DIR / "triage_results.json").write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    write_report(out, df, plain_df, pred, pred_t)
    return out


def write_report(out, df, plain_df, pred, pred_t) -> None:
    y = df["label"].tolist()
    ci, cit = out["nested_ci"], out["nested_text_only_ci"]
    n, nt = out["nested"], out["nested_text_only"]
    L = ["# 06 — Triage classification: feature-engineered baselines", "",
         f"Data: {out['n_unique_texts']} unique texts ({out['n_rows']} rows, the rest are the same text with different "
         f"coordinates) in {out['n_families']} scenario families; classes = 5 care types + `ask_followup` "
         "(rows with no label and a follow-up question). Labels are the interim CSV vocabulary (not organizer-approved).", "",
         "**Protocol.** Leave-one-family-out (LOFO): every test text comes from a scenario family never seen in training, "
         "in any language. Model/feature choice is made by an inner LOFO inside each training set (nested), selecting "
         "lexicographically on emergency recall, then macro-F1. 95% intervals resample whole families (cluster bootstrap, 2000×). "
         "With 20 families the intervals are wide; treat everything here as a regression test, not as evidence of clinical safety.", "",
         "## Headline (nested LOFO, honest estimate)", "",
         "| Model family | Macro-F1 (95% CI) | Accuracy (95% CI) | Emergency recall | Emergency FN / 9 | Over-triage to 112 |",
         "|---|---|---|---:|---:|---:|",
         f"| Majority class | {out['majority_baseline']['macro_f1']:.3f} | {out['majority_baseline']['accuracy']:.3f} | 0.000 | 9 | 0 |",
         f"| Text features only | {nt['macro_f1']:.3f} ({cit['macro_f1'][0]:.2f}–{cit['macro_f1'][1]:.2f}) | {nt['accuracy']:.3f} "
         f"({cit['accuracy'][0]:.2f}–{cit['accuracy'][1]:.2f}) | {nt['emergency_recall']:.3f} | {nt['emergency_fn']} | {nt['over_triage']} |",
         f"| Text + concept features* | {n['macro_f1']:.3f} ({ci['macro_f1'][0]:.2f}–{ci['macro_f1'][1]:.2f}) | {n['accuracy']:.3f} "
         f"({ci['accuracy'][0]:.2f}–{ci['accuracy'][1]:.2f}) | {n['emergency_recall']:.3f} | {n['emergency_fn']} | {n['over_triage']} |", "",
         "\\* The concept registry was written while reading these same utterances, so any configuration containing concept "
         "features is optimistic. Only the text-only row is free of that contamination.", "",
         "## All configurations, plain LOFO (selection-biased, for comparison only)", "", _md(plain_df, index=False), "",
         "## Repeated grouped 3-fold CV (10 random family partitions, modal config "
         f"`{out['modal_config'][0]}|{out['modal_config'][1]}`)", ""]
    rg = out["repeated_grouped"]
    L += [f"Macro-F1 mean {np.mean(rg['macro_f1']):.3f} (min {min(rg['macro_f1']):.3f}, max {max(rg['macro_f1']):.3f}); "
          f"emergency recall mean {np.mean(rg['emergency_recall']):.3f} (min {min(rg['emergency_recall']):.3f}); "
          f"emergency FN per partition {rg['emergency_fn']}. The spread shows how much the choice of family partition moves the result.", "",
          "## Approved folds A/B/C (modal config)", "", _md(pd.DataFrame(out["approved_folds"]), index=False), "",
          "## Per-family result (nested LOFO, text + concepts)", "", _md(pd.DataFrame(out["per_family"]), index=False), "",
          "## Confusion matrix (nested LOFO, text + concepts)", "", _md(_confusion(y, pred)), "",
          "## Confusion matrix (nested LOFO, text only)", "", _md(_confusion(y, pred_t)), "",
          "## Per-language accuracy (nested, text + concepts)", "", json.dumps(out["per_language"]), "",
          f"## Urgency", "",
          f"In this dataset urgency is a function of care type: {out['care_type_to_urgency_is_function']}. "
          "So urgency is derived from the predicted care type through the taxonomy pair rules rather than modelled "
          f"separately (derived-urgency exact match {out['urgency_derived_exact']:.3f}). A separate urgency model would "
          "only re-learn care type and cannot be validated independently here.", "",
          f"## Latency (single text, CPU)", "", f"p50 {out['latency_ms']['p50']:.2f} ms, p95 {out['latency_ms']['p95']:.2f} ms.", "",
          "## Misclassified texts (nested LOFO, text only)", ""]
    for r in df[df["pred_text_only"] != df["label"]].itertuples():
        L.append(f"- [{r.family}/{r.language}] `{r.text}` → true `{r.label}`, predicted `{r.pred_text_only}`")
    L += ["", "## Not done / blocked", "",
          "- Pretrained multilingual encoders (e5, BGE-M3, MuRIL, XLM-R, …) could not be run: this workspace has no GPU and "
          "cannot reach Hugging Face. See `scripts/gpu_encoder_eval.py` (runs the same LOFO protocol on your GPU machine).",
          "- Safety: emergency handling must not rely on this classifier; Stage 5 defines the hard-rule path.", ""]
    (REPORTS_DIR / "06_triage.md").write_text("\n".join(L), encoding="utf-8")
