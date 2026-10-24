"""Expected information gain of a follow-up question over the label distribution of retrieved neighbours.

Neighbours i = 1..k carry weights w_i (sum 1), labels y_i, and, for a question q, an answer distribution p_i(a).
P(y)      = sum_i w_i [y_i = y]
P(a | q)  = sum_i w_i p_i(a)
P(y|a,q)  = sum_i w_i p_i(a) [y_i = y] / P(a|q)
IG(q)     = H(Y) - sum_a P(a|q) H(Y | a, q)          (bits)
score(q)  = IG(q) + lam * danger(q)                    (danger questions are asked first by construction)

Only an answer model estimated from real data may be passed in (e.g. DDXPlus evidence presence per patient). Nothing
here invents probabilities; with no answer model the caller must fall back to the vetted question order.
"""
from __future__ import annotations

import math
from collections import defaultdict


def entropy(dist: dict) -> float:
    return -sum(p * math.log2(p) for p in dist.values() if p > 0)


def label_dist(labels: list, weights: list[float]) -> dict:
    d: dict = defaultdict(float)
    for y, w in zip(labels, weights):
        d[y] += w
    z = sum(d.values())
    return {y: v / z for y, v in d.items()}


def information_gain(labels: list, weights: list[float], answer_probs: list[dict]) -> float:
    """answer_probs[i] maps answer -> p_i(answer) for neighbour i."""
    h0 = entropy(label_dist(labels, weights))
    answers = {a for p in answer_probs for a in p}
    h_cond = 0.0
    for a in answers:
        ws = [w * p.get(a, 0.0) for w, p in zip(weights, answer_probs)]
        pa = sum(ws)
        if pa <= 0:
            continue
        h_cond += pa * entropy(label_dist(labels, ws))
    return h0 - h_cond


def rank_questions(labels, weights, candidates: dict[str, list[dict]], danger: dict[str, float] | None = None,
                   lam: float = 10.0) -> list[tuple[str, float]]:
    danger = danger or {}
    scored = [(q, information_gain(labels, weights, ap) + lam * danger.get(q, 0.0)) for q, ap in candidates.items()]
    return sorted(scored, key=lambda x: -x[1])
