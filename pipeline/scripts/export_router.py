"""Fit the final e5-head router on all 66 unique CareCompass texts and export it for the backend.

    python scripts/export_router.py --model-dir <.../multilingual-e5-base> --report reports/08_embed_router.md

Outputs
  backend/app/models/router_e5_lr.json   weights + class order + two emergency thresholds (tau_ask, tau_emergency)
  reports/08_embed_router.md             LOFO table, emergency sweep, how the thresholds were chosen
Thresholds are read off the leave-one-family-out emergency scores, never off the training fit:
  tau_ask       = largest tau with emergency recall 9/9 (a miss is the costly error) -> triggers the danger-sign question
  tau_emergency = smallest tau with zero false alarms in LOFO                        -> triggers the 112 path on its own
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "src"))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))
from ccpipe.triage.data import CLASSES, load_unique  # noqa: E402
from app.services.onnx_embed import OnnxEmbedder  # noqa: E402
from train_router_embed import EM, lofo, metrics  # noqa: E402

C_MULTI, C_EMERG, WEIGHT = 0.3, 0.03, "balanced"


def lofo_emergency(df, emb, C):
    """Binary emergency head on standardised embeddings (report 06c protocol): held-out family each time."""
    from sklearn.preprocessing import StandardScaler
    fam = df["family"].to_numpy()
    em = (df["label"] == EM).to_numpy()
    s = np.zeros(len(df))
    for g in sorted(set(fam)):
        te, tr = np.where(fam == g)[0], np.where(fam != g)[0]
        sc = StandardScaler().fit(emb[tr])
        clf = LogisticRegression(C=C, class_weight=WEIGHT, max_iter=5000).fit(sc.transform(emb[tr]), em[tr])
        s[te] = clf.predict_proba(sc.transform(emb[te]))[:, 1]
    return s


def boot_ci(df, P, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    fams = sorted(set(df["family"]))
    y = df["label"].to_numpy()
    pred = np.array(CLASSES)[P.argmax(1)]
    from sklearn.metrics import f1_score
    out = []
    for _ in range(n):
        pick = rng.choice(fams, len(fams))
        idx = np.concatenate([np.where(df["family"].to_numpy() == f)[0] for f in pick])
        out.append(f1_score(y[idx], pred[idx], labels=CLASSES, average="macro", zero_division=0))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--report", default=str(ROOT / "pipeline" / "reports" / "08_embed_router.md"))
    ap.add_argument("--out", default=str(ROOT / "backend" / "app" / "models" / "router_e5_lr.json"))
    a = ap.parse_args()
    df = load_unique()
    emb = OnnxEmbedder(a.model_dir).encode(df["text"].tolist())
    P = lofo(df, lambda tr, te: (emb[tr], emb[te]), C_MULTI, WEIGHT)
    m = metrics(df, P)
    lo, hi = boot_ci(df, P)
    em = (df["label"] == EM).to_numpy()
    s = lofo_emergency(df, emb, C_EMERG)
    from sklearn.metrics import roc_auc_score
    em_auc = float(roc_auc_score(em, s))
    rows = []
    for tau in np.round(np.arange(0.05, 0.91, 0.05), 2):
        tp = int((s[em] >= tau).sum()); fp = int((s[~em] >= tau).sum())
        rows.append((float(tau), tp, int(em.sum()) - tp, fp, tp / em.sum(), tp / (tp + fp) if tp + fp else float("nan")))
    full = [r for r in rows if r[2] == 0]
    tau_ask = max(r[0] for r in full) if full else 0.05
    clean = [r for r in rows if r[3] == 0 and r[1] > 0]
    tau_em = min(r[0] for r in clean) if clean else 0.9
    clf = LogisticRegression(C=C_MULTI, class_weight=WEIGHT, max_iter=5000).fit(emb, df["label"].to_numpy())
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(emb)
    eclf = LogisticRegression(C=C_EMERG, class_weight=WEIGHT, max_iter=5000).fit(sc.transform(emb), em)
    art = {"version": "e5-lr-v2", "encoder": "multilingual-e5-base", "classes": list(clf.classes_), "coef": clf.coef_.round(6).tolist(),
           "intercept": clf.intercept_.round(6).tolist(),
           "emergency": {"mean": sc.mean_.round(6).tolist(), "scale": sc.scale_.round(6).tolist(), "coef": eclf.coef_[0].round(6).tolist(),
                         "intercept": float(eclf.intercept_[0])},
           "tau_ask": tau_ask, "tau_emergency": tau_em, "train_texts": len(df),
           "lofo": {**m, "macro_f1_ci95": [lo, hi], "emergency_auroc": em_auc}}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(art))
    md = [f"# 08 — Frozen multilingual-e5-base head: LOFO result and emergency thresholds\n",
          "Features: `multilingual-e5-base` sentence embeddings (ONNX, CPU), logistic regression, care type: C=0.3 balanced; emergency score: separate binary head on standardised embeddings, C=0.03 balanced. Same 66 texts, 20 families and leave-one-family-out protocol as report 06.\n",
          f"| Model | Macro-F1 (95% family-bootstrap CI) | Accuracy | Emergency recall | Over-triage to 112 | Emergency AUROC |\n|---|---|---|---|---|---|",
          f"| char n-gram (report 06, nested) | 0.416 (0.25–0.52) | 0.470 | 0.556 | 2 | 0.938 |",
          f"| **e5 head (this report)** | **{m['macro_f1']:.3f}** ({lo:.2f}–{hi:.2f}) | {m['accuracy']:.3f} | {m['emergency_recall']:.3f} | {m['over_triage']} | {em_auc:.3f} (binary head) |\n",
          "Caveat: C was picked after looking at six e5 configurations on these same folds (all six beat the char baseline: F1 0.54–0.68), so the headline is optimistic; the gain over char n-grams is not.\n",
          "## Emergency score sweep (LOFO, held-out family each time)\n", "| tau | caught | missed | false alarms | recall | precision |", "|---|---|---|---|---|---|"]
    for t, tp, fn, fp, rec, prec in rows:
        md.append(f"| {t:.2f} | {tp} | {fn} | {fp} | {rec:.3f} | {prec:.3f} |")
    md += ["", f"**tau_ask = {tau_ask}** (largest tau that still catches 9/9): a score at or above it asks one danger-sign question.",
           f"**tau_emergency = {tau_em}** (smallest tau with zero false alarms in LOFO): a score at or above it goes to the 112 path by itself.",
           "Both come from held-out scores. With 9 emergency texts in 3 families the intervals are wide; the rules and the LLM stay in front of this score and it can only raise urgency."]
    Path(a.report).write_text("\n".join(md) + "\n")
    print(json.dumps({k: art[k] for k in ("tau_ask", "tau_emergency", "lofo")}, indent=1))
    print("\n".join(md[-22:]))


if __name__ == "__main__":
    main()
