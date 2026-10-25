"""Measure the dialogue intent gate on pipeline/eval/intent_probe.jsonl.

    uv run python -m eval.intent_probe [--show-misses]

health-intent recall = share of health/care probes that classify_turn does NOT call general/greeting.
false-health rate    = share of non-health probes that classify_turn calls health.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.dialogue import classify_turn, extract_concepts, _n

PROBE = Path(__file__).resolve().parents[2] / "pipeline" / "eval" / "intent_probe.jsonl"


def load() -> list[dict]:
    return [json.loads(l) for l in PROBE.read_text(encoding="utf-8").splitlines() if l.strip()]


def predict(text: str) -> str:
    concepts, _ = extract_concepts(_n(text))
    act, _ = classify_turn(text, False, concepts)
    return act


def run() -> dict:
    rows = load()
    out = {"n": len(rows), "misses": [], "false_health": []}
    pos = [r for r in rows if r["label"] == "health"]
    neg = [r for r in rows if r["label"] == "non_health"]
    for r in pos:
        act = predict(r["text"])
        if act in ("general", "greeting"):
            out["misses"].append((r["text"], act))
    for r in neg:
        act = predict(r["text"])
        if act == "health":
            out["false_health"].append((r["text"], act))
    out["health_recall"] = 1 - len(out["misses"]) / len(pos)
    out["false_health_rate"] = len(out["false_health"]) / len(neg)
    out["n_pos"], out["n_neg"] = len(pos), len(neg)
    return out


def calibrate_encoder(path: str) -> None:
    """Score every probe with the optional encoder net alone and print the best margin (use it for INTENT_ENCODER_MARGIN)."""
    import os

    os.environ["INTENT_ENCODER_PATH"] = path
    from app.services.semantic_intent import get_semantic_intent

    net = get_semantic_intent()
    if net is None:
        print("encoder net unavailable (install sentence-transformers + torch, check the path)")
        return
    rows = load()
    scored = [(net.score(r["text"]), r["label"] == "health") for r in rows]
    pos, neg = sum(y for _, y in scored), sum(not y for _, y in scored)
    best = None
    for m in sorted({round(s, 3) for s, _ in scored}):
        rec = sum(1 for s, y in scored if y and s > m) / pos
        fpr = sum(1 for s, y in scored if not y and s > m) / neg
        if fpr <= 0.03 and (best is None or rec > best[1]):
            best = (m, rec, fpr)
    print(f"encoder-only: best margin with false-health<=3% -> margin={best[0]:.3f} recall={best[1]:.3f} fpr={best[2]:.3f}" if best else "no margin reaches 3% false-health")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-misses", action="store_true")
    ap.add_argument("--encoder", help="path to a local sentence-transformers model: calibrate the optional semantic net")
    a = ap.parse_args()
    if a.encoder:
        calibrate_encoder(a.encoder)
        raise SystemExit
    res = run()
    print(f"probes={res['n']} (pos={res['n_pos']}, neg={res['n_neg']})")
    print(f"health-intent recall : {res['health_recall']:.3f}  ({len(res['misses'])} missed)")
    print(f"false-health rate    : {res['false_health_rate']:.3f}  ({len(res['false_health'])} false)")
    if a.show_misses:
        for t, act in res["misses"]:
            print("  MISS", act, "|", t)
        for t, act in res["false_health"]:
            print("  FALSE", act, "|", t)
