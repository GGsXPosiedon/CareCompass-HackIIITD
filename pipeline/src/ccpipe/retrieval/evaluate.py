"""Leave-one-family-out retrieval baselines: BM25, dense, and RRF-hybrid kNN routing.

For each held-out text the corpus excludes its whole scenario family (so translations / paraphrases cannot leak).
The prediction is the weighted vote of the top-k neighbours' labels.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..triage import cv
from .bm25 import BM25
from .fusion import rrf, softmax_weights


def _vote(labels: list[str], w: np.ndarray) -> str:
    agg: dict[str, float] = {}
    for y, x in zip(labels, w):
        agg[y] = agg.get(y, 0.0) + float(x)
    return max(sorted(agg), key=lambda y: agg[y])


def lofo_retrieval(df: pd.DataFrame, q_emb: np.ndarray, p_emb: np.ndarray, k: int = 5, temp: float = 0.05):
    """Returns {method: predictions} and the neighbour indices used by the hybrid ranker."""
    texts, labels, fams = df["text"].tolist(), df["label"].tolist(), df["family"].to_numpy()
    out = {m: np.empty(len(df), dtype=object) for m in ("bm25", "dense", "hybrid")}
    hybrid_nn = {}
    for fam in sorted(set(fams)):
        corpus = np.where(fams != fam)[0]
        bm = BM25([texts[j] for j in corpus])
        for i in np.where(fams == fam)[0]:
            sb = bm.scores(texts[i])
            sd = p_emb[corpus] @ q_emb[i]
            for name, s in (("bm25", sb), ("dense", sd), ("hybrid", rrf(sb, sd))):
                top = np.argsort(-s, kind="stable")[:k]
                if name == "bm25":
                    w = s[top] + 1e-9
                    w = w / w.sum()
                elif name == "dense":
                    w = softmax_weights(s[top], temp)
                else:
                    w = s[top] / s[top].sum()
                    hybrid_nn[int(i)] = [int(corpus[t]) for t in top]
                out[name][i] = _vote([labels[corpus[t]] for t in top], w)
    return out, hybrid_nn


def report_rows(df: pd.DataFrame, preds: dict[str, np.ndarray]) -> pd.DataFrame:
    rows = []
    for name, p in preds.items():
        s = cv.score(df["label"].tolist(), list(p))
        rows.append({"method": name, "macro_f1": s["macro_f1"], "accuracy": s["accuracy"],
                     "emergency_recall": s.get("emergency_recall"), "emergency_fn": s.get("emergency_fn"), "over_triage": s.get("over_triage")})
    return pd.DataFrame(rows)
