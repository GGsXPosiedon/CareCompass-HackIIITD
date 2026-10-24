"""Leave-one-family-out (LOFO) evaluation, nested model selection, cluster bootstrap."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedGroupKFold

from .data import CLASSES, FOLLOWUP
from .zoo import all_configs, build

EMERGENCY = "emergency_112"


def predict_groups(df: pd.DataFrame, feature_set: str, clf: str, splits) -> np.ndarray:
    pred = np.empty(len(df), dtype=object)
    for train_idx, test_idx in splits:
        model = build(feature_set, clf)
        model.fit(df["text"].iloc[train_idx].tolist(), df["label"].iloc[train_idx].tolist())
        pred[test_idx] = model.predict(df["text"].iloc[test_idx].tolist())
    return pred


def lofo_splits(groups: np.ndarray):
    for g in sorted(set(groups)):
        test = np.where(groups == g)[0]
        yield np.where(groups != g)[0], test


def score(y_true, y_pred) -> dict:
    em = [t == EMERGENCY for t in y_true]
    em_total = sum(em)
    em_hit = sum(1 for t, p in zip(y_true, y_pred) if t == EMERGENCY and p == EMERGENCY)
    return {
        "macro_f1": float(f1_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "emergency_recall": em_hit / em_total if em_total else 1.0,
        "emergency_fn": em_total - em_hit,
        # an emergency text sent to a non-emergency class is the dangerous direction; the reverse is over-triage
        "over_triage": sum(1 for t, p in zip(y_true, y_pred) if p == EMERGENCY and t != EMERGENCY),
    }


def _cache_path(cache_dir: Path, fs: str, clf: str) -> Path:
    return cache_dir / f"{fs.replace('*', 'x').replace('+', '_')}__{clf}.json"


def _fit_predict(df: pd.DataFrame, fs: str, clf: str, drop: set[str], target: str) -> list[str]:
    fam = df["family"].to_numpy()
    train = np.where(~np.isin(fam, list(drop)))[0]
    test = np.where(fam == target)[0]
    model = build(fs, clf)
    model.fit(df["text"].iloc[train].tolist(), df["label"].iloc[train].tolist())
    return model.predict(df["text"].iloc[test].tolist()).tolist()


def pair_predictions(df: pd.DataFrame, fs: str, clf: str, cache_dir: Path, deadline: float | None = None) -> dict | None:
    """Predictions for family g from a model trained without {f, g} (f = '-' means without g only).

    Outer LOFO needs key ('-', g); the inner selection for outer fold f needs ('f', g) for all g != f. Each
    model is fit once and persisted, so the nested run is resumable. Returns None if the deadline hit first."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, fs, clf)
    cache = json.loads(path.read_text()) if path.exists() else {}
    fams = sorted(df["family"].unique())
    todo = [(f, g) for f in ["-"] + fams for g in fams if f != g and f"{f}|{g}" not in cache]
    for f, g in todo:
        if deadline is not None and time.time() > deadline:
            path.write_text(json.dumps(cache))
            return None
        cache[f"{f}|{g}"] = _fit_predict(df, fs, clf, {g} | ({f} if f != "-" else set()), g)
    if todo:
        path.write_text(json.dumps(cache))
    return cache


def _assemble(df: pd.DataFrame, cache: dict, outer: str, skip: str | None = None) -> tuple[list[str], list[str]]:
    y_true, y_pred = [], []
    for g in sorted(df["family"].unique()):
        if g == skip:
            continue
        idx = np.where(df["family"].to_numpy() == g)[0]
        y_true += df["label"].iloc[idx].tolist()
        y_pred += cache[f"{outer}|{g}"]
    return y_true, y_pred


def nested_from_cache(df: pd.DataFrame, configs, cache_dir: Path) -> tuple[np.ndarray, list[tuple[str, str]]]:
    caches = {c: pair_predictions(df, c[0], c[1], cache_dir) for c in configs}
    pred = np.empty(len(df), dtype=object)
    chosen = []
    for f in sorted(df["family"].unique()):
        best, best_key = None, None
        for rank, c in enumerate(configs):
            yt, yp = _assemble(df, caches[c], f, skip=f)
            s = score(yt, yp)
            key = (round(s["emergency_recall"], 6), round(s["macro_f1"], 6), -rank)
            if best_key is None or key > best_key:
                best, best_key = c, key
        chosen.append(best)
        idx = np.where(df["family"].to_numpy() == f)[0]
        pred[idx] = caches[best][f"-|{f}"]
    return pred, chosen


def plain_lofo_from_cache(df: pd.DataFrame, cache: dict) -> np.ndarray:
    pred = np.empty(len(df), dtype=object)
    for g in sorted(df["family"].unique()):
        pred[np.where(df["family"].to_numpy() == g)[0]] = cache[f"-|{g}"]
    return pred


def cluster_bootstrap(df: pd.DataFrame, pred: np.ndarray, n: int = 2000, seed: int = 0) -> dict:
    """Resample whole families (the unit of independence) with replacement."""
    rng = np.random.default_rng(seed)
    fams = sorted(df["family"].unique())
    idx = {f: np.where(df["family"].to_numpy() == f)[0] for f in fams}
    y = df["label"].to_numpy()
    out = {"macro_f1": [], "accuracy": []}
    for _ in range(n):
        pick = rng.choice(fams, size=len(fams), replace=True)
        ii = np.concatenate([idx[f] for f in pick])
        s = score(y[ii].tolist(), pred[ii].tolist())
        out["macro_f1"].append(s["macro_f1"])
        out["accuracy"].append(s["accuracy"])
    return {k: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in out.items()}


def repeated_grouped_cv(df: pd.DataFrame, feature_set: str, clf: str, repeats: int = 10) -> list[dict]:
    """Different family partitions (stratified by care type) to show how much the fold choice matters."""
    results = []
    y = df["label"].to_numpy()
    fam_label = df.drop_duplicates("family").set_index("family")["label"]
    for seed in range(repeats):
        skf = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed)
        splits = list(skf.split(df["text"], y, groups=df["family"]))
        pred = predict_groups(df, feature_set, clf, splits)
        results.append(score(y.tolist(), pred.tolist()))
    return results


def latency_ms(feature_set: str, clf: str, df: pd.DataFrame, reps: int = 200) -> dict:
    model = build(feature_set, clf)
    model.fit(df["text"].tolist(), df["label"].tolist())
    texts = df["text"].tolist()
    times = []
    for i in range(reps):
        t0 = time.perf_counter()
        model.predict([texts[i % len(texts)]])
        times.append((time.perf_counter() - t0) * 1000)
    return {"p50": float(np.percentile(times, 50)), "p95": float(np.percentile(times, 95))}
