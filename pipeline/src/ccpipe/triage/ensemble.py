"""Learned weighted combination of several models:  z_c = sum_m w_m * log p_m(c) + b_c,  p = softmax(z).

The weights w_m >= 0 and biases b_c are fitted by gradient-based minimisation (L-BFGS-B) of a cost-sensitive
cross-entropy: the emergency class carries an extra loss multiplier, so a missed emergency is punished more than
a false alarm. Only M weights + 6 biases are learned, with an L2 pull toward the plain average, because there are
only 66 texts. Evaluated leave-one-family-out: the held-out family never influences the weights.

Caveat: the input probabilities are themselves out-of-fold predictions from the base models, so this is the usual
stacking approximation, not a fully nested estimate; treat gains as indicative.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .cv import score
from .data import CLASSES

EPS = 1e-6
EMERGENCY_IDX = CLASSES.index("emergency_112")


def _logits(logp: np.ndarray, w: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.tensordot(w, logp, axes=(0, 0)) + b  # (M,) x (M,N,C) -> (N,C)


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def fit_stacker(probs: list[np.ndarray], y_idx: np.ndarray, emergency_weight: float = 3.0, l2: float = 0.05):
    M, (N, C) = len(probs), probs[0].shape
    logp = np.log(np.stack(probs) + EPS)
    counts = np.bincount(y_idx, minlength=C).clip(1)
    cw = N / (C * counts)
    cw[EMERGENCY_IDX] *= emergency_weight
    sw = cw[y_idx]

    def objective(theta):
        w, b = theta[:M], theta[M:]
        p = _softmax(_logits(logp, w, b))
        nll = -np.log(p[np.arange(N), y_idx] + EPS)
        loss = (sw * nll).sum() / sw.sum() + l2 * (((w - 1.0 / M) ** 2).sum() + (b ** 2).sum())
        onehot = np.zeros_like(p)
        onehot[np.arange(N), y_idx] = 1
        g_z = (p - onehot) * sw[:, None] / sw.sum()
        g_w = np.einsum("nc,mnc->m", g_z, logp) + 2 * l2 * (w - 1.0 / M)
        g_b = g_z.sum(axis=0) + 2 * l2 * b
        return loss, np.concatenate([g_w, g_b])

    theta0 = np.concatenate([np.full(M, 1.0 / M), np.zeros(C)])
    res = minimize(objective, theta0, jac=True, method="L-BFGS-B", bounds=[(0, None)] * M + [(None, None)] * C)
    return res.x[:M], res.x[M:]


def predict_stacker(probs: list[np.ndarray], w: np.ndarray, b: np.ndarray) -> np.ndarray:
    return _softmax(_logits(np.log(np.stack(probs) + EPS), w, b))


def lofo_stack(df: pd.DataFrame, probs: list[np.ndarray], emergency_weight: float = 3.0, tau: float = 0.10):
    """Returns (final labels, stacked probabilities, per-fold weights). Emergency if p_emergency >= tau."""
    y_idx = np.array([CLASSES.index(l) for l in df["label"]])
    fam = df["family"].to_numpy()
    out = np.zeros((len(df), len(CLASSES)))
    weights = []
    for g in sorted(set(fam)):
        te = fam == g
        w, b = fit_stacker([p[~te] for p in probs], y_idx[~te], emergency_weight)
        out[te] = predict_stacker([p[te] for p in probs], w, b)
        weights.append(w)
    labels = np.array([CLASSES[i] for i in out.argmax(1)], dtype=object)
    labels[out[:, EMERGENCY_IDX] >= tau] = "emergency_112"
    return labels, out, np.array(weights)


def compare(df: pd.DataFrame, named_probs: dict[str, np.ndarray], emergency_weight: float = 3.0, tau: float = 0.10) -> pd.DataFrame:
    y = df["label"].tolist()
    rows = []
    for name, p in named_probs.items():
        labels = np.array([CLASSES[i] for i in p.argmax(1)], dtype=object)
        rows.append({"model": name, **score(y, labels.tolist())})
    avg = np.mean(np.stack(list(named_probs.values())), axis=0)
    rows.append({"model": "plain average", **score(y, [CLASSES[i] for i in avg.argmax(1)])})
    labels, _, w = lofo_stack(df, list(named_probs.values()), emergency_weight, tau)
    rows.append({"model": f"learned stack (tau={tau})", **score(y, labels.tolist())})
    return pd.DataFrame(rows)
