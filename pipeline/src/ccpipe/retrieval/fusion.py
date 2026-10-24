"""Rank fusion and neighbour weighting.

RRF(d) = sum_over_rankers 1 / (k + rank(d)),  k = 60 (rank starts at 1)
w_i    = softmax(score_i / T) over the retrieved neighbours
"""
from __future__ import annotations

import numpy as np


def ranks(scores: np.ndarray) -> np.ndarray:
    """1-based rank, best first. Ties share the order of np.argsort (stable)."""
    order = np.argsort(-scores, kind="stable")
    r = np.empty(len(scores), dtype=int)
    r[order] = np.arange(1, len(scores) + 1)
    return r


def rrf(*score_lists: np.ndarray, k: int = 60) -> np.ndarray:
    total = np.zeros(len(score_lists[0]))
    for s in score_lists:
        total += 1.0 / (k + ranks(s))
    return total


def softmax_weights(scores: np.ndarray, temperature: float) -> np.ndarray:
    z = (scores - scores.max()) / temperature
    e = np.exp(z)
    return e / e.sum()
