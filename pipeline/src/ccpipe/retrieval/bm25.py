"""Okapi BM25 over the pipeline tokeniser (so Devanagari / Hinglish normalise the same way as the extractor).

score(q, d) = sum_t IDF(t) * f(t,d) * (k1 + 1) / (f(t,d) + k1 * (1 - b + b * |d| / avgdl))
IDF(t)      = ln((N - n_t + 0.5) / (n_t + 0.5) + 1)
"""
from __future__ import annotations

import math
from collections import Counter

import numpy as np

from ..extraction.registry import tokenize


def toks(text: str) -> list[str]:
    return [t for t, _, _ in tokenize(text)]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(toks(d)) for d in docs]
        self.len = np.array([sum(c.values()) for c in self.tf], dtype=float)
        self.avgdl = float(self.len.mean()) if len(docs) else 0.0
        df = Counter(t for c in self.tf for t in c)
        n = len(docs)
        self.idf = {t: math.log((n - v + 0.5) / (v + 0.5) + 1.0) for t, v in df.items()}

    def scores(self, query: str) -> np.ndarray:
        out = np.zeros(len(self.tf))
        for t in set(toks(query)):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i, c in enumerate(self.tf):
                f = c.get(t, 0)
                if f:
                    out[i] += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avgdl))
        return out
