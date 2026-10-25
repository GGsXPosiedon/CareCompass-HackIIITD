"""LOFO evaluation of encoder-embedding heads for care type + emergency score (CPU, ONNX e5; no torch).

    python scripts/train_router_embed.py --model-dir <.../multilingual-e5-base> [--out data/processed/router_embed_lofo.json]

Protocol identical to reports/06_triage.md: leave-one-family-out over the 66 unique CareCompass texts; the gold set is tiny so
every number carries a family-bootstrap interval and nothing here is tuned on the held-out family.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "src"))
sys.path.insert(0, str(ROOT / "backend"))
from ccpipe.triage.data import CLASSES, load_unique  # noqa: E402
from app.services.onnx_embed import OnnxEmbedder  # noqa: E402

EM = "emergency_112"


def lofo(df, make_feats, C, weight):
    fam = df["family"].to_numpy()
    y = df["label"].to_numpy()
    P = np.zeros((len(df), len(CLASSES)))
    for g in sorted(set(fam)):
        te = np.where(fam == g)[0]
        tr = np.where(fam != g)[0]
        Xtr, Xte = make_feats(tr, te)
        clf = LogisticRegression(C=C, class_weight=weight, max_iter=2000)
        clf.fit(Xtr, y[tr])
        pr = clf.predict_proba(Xte)
        for j, c in enumerate(clf.classes_):
            P[te, CLASSES.index(c)] = pr[:, j]
    return P


def metrics(df, P):
    y = df["label"].to_numpy()
    pred = np.array(CLASSES)[P.argmax(1)]
    em = y == EM
    s = P[:, CLASSES.index(EM)]
    return {
        "macro_f1": float(f1_score(y, pred, labels=CLASSES, average="macro", zero_division=0)),
        "accuracy": float(accuracy_score(y, pred)),
        "emergency_recall": float((pred[em] == EM).mean()),
        "over_triage": int(((pred == EM) & ~em).sum()),
        "emergency_auroc": float(roc_auc_score(em, s)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--out", default=str(ROOT / "pipeline" / "data" / "processed" / "router_embed_lofo.json"))
    a = ap.parse_args()
    df = load_unique()
    texts = df["text"].tolist()
    emb = OnnxEmbedder(a.model_dir).encode(texts)
    results = {}

    def emb_feats(tr, te):
        return emb[tr], emb[te]

    def char_feats(tr, te):
        v = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, lowercase=True)
        return v.fit_transform([texts[i] for i in tr]), v.transform([texts[i] for i in te])

    def both(tr, te):
        from scipy.sparse import csr_matrix, hstack
        v = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
        A, B = v.fit_transform([texts[i] for i in tr]), v.transform([texts[i] for i in te])
        return hstack([A, csr_matrix(emb[tr])]).tocsr(), hstack([B, csr_matrix(emb[te])]).tocsr()

    Ps = {}
    for name, feats in (("e5", emb_feats), ("char", char_feats), ("e5+char", both)):
        for C in (1, 10, 100):
            for w in (None, "balanced"):
                P = lofo(df, feats, C, w)
                Ps[(name, C, w)] = P
                results[f"{name}|C={C}|{w}"] = metrics(df, P)
    # probability-average ensemble of the best embedding head and the char head
    for ce, cc in ((10, 10), (100, 10), (100, 100)):
        P = (Ps[("e5", ce, "balanced")] + Ps[("char", cc, "balanced")]) / 2
        Ps[("ens", ce, cc)] = P
        results[f"ens(e5 C={ce}, char C={cc})|balanced"] = metrics(df, P)
    for k, v in sorted(results.items(), key=lambda kv: -kv[1]["macro_f1"])[:14]:
        print(f"{k:44s} F1={v['macro_f1']:.3f} acc={v['accuracy']:.3f} emRecall={v['emergency_recall']:.3f} overTriage={v['over_triage']:2d} emAUROC={v['emergency_auroc']:.3f}")
    print("-- best by emergency AUROC")
    for k, v in sorted(results.items(), key=lambda kv: -kv[1]["emergency_auroc"])[:6]:
        print(f"{k:44s} emAUROC={v['emergency_auroc']:.3f} F1={v['macro_f1']:.3f}")
    Path(a.out).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
