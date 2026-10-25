"""Pick the 'ask which of the two?' log-ratio margin from held-out scores (same LOFO as report 08), and store it in the router artifact.

For every held-out text: top-1 / top-2 care type (emergency excluded: it has its own path), margin = np.log(p1/p2).
Asking one question that offers exactly those two options resolves the case whenever the truth is among them, so a text is worth a
question when P(top-1 correct | margin) is below `--target` (default 0.65). tau_margin = the largest margin whose bucket stays below it.
Usage: python scripts/calibrate_ambiguity.py --model-dir <models>/multilingual-e5-base
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "src")); sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(Path(__file__).parent))
from ccpipe.triage.data import CLASSES, load_unique  # noqa: E402
from app.services.onnx_embed import OnnxEmbedder  # noqa: E402
from train_router_embed import lofo  # noqa: E402

ART = ROOT / "backend" / "app" / "models" / "router_e5_lr.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--target", type=float, default=0.65)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    df = load_unique()
    emb = OnnxEmbedder(a.model_dir).encode(df["text"].tolist())
    P = lofo(df, lambda tr, te: (emb[tr], emb[te]), 0.3, "balanced")
    em = CLASSES.index("emergency_112")
    y = df["label"].to_numpy()
    af = CLASSES.index("ask_followup")
    keep = (y != "emergency_112") & (y != "ask_followup")   # emergencies: emergency score; vague openers: the dialogue layer
    P = P.copy(); P[:, em] = 0; P[:, af] = 0; P = P / P.sum(1, keepdims=True)
    order = np.argsort(-P, axis=1)
    top1, top2 = np.array(CLASSES)[order[:, 0]], np.array(CLASSES)[order[:, 1]]
    p1, p2 = P[np.arange(len(P)), order[:, 0]], P[np.arange(len(P)), order[:, 1]]
    margin = np.log(p1 / p2)  # scale-free: the head's probabilities are flat (C=0.3), so absolute differences are ~0.01
    print("top-1 prob quantiles", np.round(np.quantile(p1[keep], [0.1, 0.5, 0.9]), 3), "log-ratio quantiles", np.round(np.quantile(margin[keep], [0.1, 0.25, 0.5, 0.75, 0.9]), 3))
    ok1, ok2 = top1 == y, (top1 == y) | (top2 == y)
    print(f"{keep.sum()} non-emergency texts; top-1 acc {ok1[keep].mean():.3f}; truth in top-2 {ok2[keep].mean():.3f}")
    print("margin<  | asked | top1 acc among asked | top-2 contains truth | top1 acc among NOT asked")
    best = 0.0
    rows = []
    for m in np.round(np.quantile(margin[keep], [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]), 4):
        m = float(m)
        sel = keep & (margin < m)
        rest = keep & ~(margin < m)
        if sel.sum() == 0:
            continue
        rows.append((m, int(sel.sum()), ok1[sel].mean(), ok2[sel].mean(), ok1[rest].mean() if rest.sum() else float("nan")))
        print(f"{m:7.4f}  | {sel.sum():5d} | {ok1[sel].mean():.3f} | {ok2[sel].mean():.3f} | {rows[-1][4]:.3f}")
        if ok1[sel].mean() < a.target:
            best = m
    print(f"tau_margin = {best} (largest margin whose asked bucket has top-1 accuracy < {a.target})")
    if a.write:
        art = json.loads(ART.read_text())
        art["tau_margin"] = best
        art["ambiguity_calibration"] = [{"margin_lt": r[0], "asked": r[1], "top1_acc_asked": round(float(r[2]), 3), "top2_has_truth": round(float(r[3]), 3), "top1_acc_rest": round(float(r[4]), 3)} for r in rows]
        ART.write_text(json.dumps(art))
        print("written to", ART)


if __name__ == "__main__":
    main()
