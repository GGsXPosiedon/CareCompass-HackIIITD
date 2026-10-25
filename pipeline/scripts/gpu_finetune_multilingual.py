r"""Two-stage GPU run: multilingual symptom adaptation on the external dataset, then the CareCompass LOFO triage test.

  Stage A  (external data, mlt_complaints.jsonl from prepare_multilingual_triage.py)
           Fine-tune the encoder + a linear head to name the DISEASE from a complaint written in English / Hinglish / Hindi /
           Marathi / Bengali / Telugu / Gujarati. This is the only learnable label in that dataset (its urgency labels are at
           chance, see reports/09), and it teaches the encoder that "bukhar", "ज्वर", "জ্বর" and "fever" are one concept.
           Fixed recipe: 2 epochs, lr 2e-5, batch 32, max_len 64, bf16 autocast, AdamW wd 0.01, 10% warm-up. No tuning on the
           CareCompass folds. A 10% held-out slice (grouped by complaint text) reports disease accuracy so you can see it learned.
  Stage B  (CareCompass, 66 texts / 20 families, leave-one-family-out; identical protocol to reports 06 and 08)
           Compare four variants per encoder: base-frozen, adapted-frozen, base-finetuned, adapted-finetuned (3 seeds each for
           fine-tuned). Fine-tuning is class-balanced with the emergency class up-weighted x3 (see --emergency-weight).
  Decision rule (written into the report): adopt the adapted encoder only if its mean macro-F1 beats the base encoder AND its
           emergency recall is not lower. Otherwise keep the frozen e5 head already in the backend.

Run (Windows, RTX 4060):  powershell -ExecutionPolicy Bypass -File pipeline\scripts\run_gpu_windows.ps1
Dry run (no torch needed; checks the data plumbing only):  python scripts/gpu_finetune_multilingual.py --dry-run
Status: written for the RTX 4060 but NOT executed anywhere yet (the build workspace has no torch/GPU); paste any error back.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ccpipe.paths import PROCESSED_DIR, PIPELINE_DIR, REPORTS_DIR
from ccpipe.triage import cv
from ccpipe.triage.data import load_unique

import gpu_encoder_eval as base  # same folder; reuses lofo_frozen / lofo_finetune / embed helpers

DEFAULT_MODELS = ["multilingual-e5-base", "muril-base-cased", "xlm-roberta-base"]
ADAPTED_DIR = PIPELINE_DIR / "models_ft"            # fine-tuned weights: large, git-ignored, never needed at serve time
RESULTS_DIR = PIPELINE_DIR / "results"               # small text outputs: COMMIT these (the GPU machine is not the dev machine)


def load_complaints(path: Path) -> pd.DataFrame:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit(f"{path} is empty: run scripts/prepare_multilingual_triage.py first")
    return df


def stage_a(model_name: str, src: str, df: pd.DataFrame, device: str, out_dir: Path, epochs=2, lr=2e-5, bs=32, seed=0) -> dict:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

    torch.manual_seed(seed); np.random.seed(seed)
    tok = AutoTokenizer.from_pretrained(src)
    enc = AutoModel.from_pretrained(src).to(device)
    diseases = sorted(df["disease"].unique())
    y = np.array([diseases.index(d) for d in df["disease"]])
    texts = [base._prefix(model_name, t) for t in df["text"]]
    # grouped hold-out: all rows with the same text go to the same side
    gid = pd.factorize(df["text"].str.lower())[0]
    rng = np.random.RandomState(seed)
    val_groups = set(rng.choice(np.unique(gid), size=max(1, int(0.1 * len(np.unique(gid)))), replace=False))
    is_val = np.array([g in val_groups for g in gid])
    tr, va = np.where(~is_val)[0], np.where(is_val)[0]
    head = nn.Linear(enc.config.hidden_size, len(diseases)).to(device)
    opt = torch.optim.AdamW(list(enc.parameters()) + list(head.parameters()), lr=lr, weight_decay=0.01)
    steps = epochs * int(np.ceil(len(tr) / bs))
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    loss_fn = nn.CrossEntropyLoss()

    def fwd(idx):
        b = tok([texts[i] for i in idx], padding=True, truncation=True, max_length=64, return_tensors="pt").to(device)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device.startswith("cuda")):
            h = enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1)
            return head(((h * m).sum(1) / m.sum(1)))

    enc.train()
    for ep in range(epochs):
        order = np.random.permutation(tr)
        total = 0.0
        for s in range(0, len(order), bs):
            idx = order[s:s + bs]
            loss = loss_fn(fwd(idx).float(), torch.tensor(y[idx], device=device))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(enc.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            total += float(loss) * len(idx)
        print(f"  stage A epoch {ep + 1}/{epochs} loss {total / len(tr):.4f}")
    enc.eval()
    correct = 0
    with torch.no_grad():
        for s in range(0, len(va), 64):
            idx = va[s:s + 64]
            correct += int((fwd(idx).argmax(-1).cpu().numpy() == y[idx]).sum())
    acc = correct / max(1, len(va))
    out_dir.mkdir(parents=True, exist_ok=True)
    enc.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)
    del enc, head, opt
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
    return {"train": int(len(tr)), "val": int(len(va)), "val_disease_acc": round(acc, 4), "classes": len(diseases)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS, help="folder names inside --models-dir")
    ap.add_argument("--models-dir", default=None)
    ap.add_argument("--complaints", default=str(PROCESSED_DIR / "mlt_complaints.jsonl"))
    ap.add_argument("--gpu-name", default="4060")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--stage-a-epochs", type=int, default=2)
    ap.add_argument("--emergency-weight", type=float, default=3.0)
    ap.add_argument("--skip-finetune", action="store_true", help="stage A + frozen comparison only (faster)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    comp = load_complaints(Path(a.complaints))
    gold = load_unique()
    y = gold["label"].tolist()
    print(f"complaints: {len(comp)} ({comp['lang'].value_counts().to_dict()}), gold texts: {len(gold)}")
    if a.dry_run:
        X = base.embed_dry(gold["text"].tolist())
        p, _ = base.lofo_frozen(gold, X)
        print("dry-run frozen hash LOFO:", {k: round(v, 3) for k, v in cv.score(y, p.tolist()).items() if isinstance(v, float)})
        return

    device = base.pick_device(a.gpu_name)
    rows, notes = [], []
    for name in a.models:
        t0 = time.time()
        src = base._resolve(name, a.models_dir)
        adapted = ADAPTED_DIR / f"{name}-mlt"
        print(f"== {name}: stage A")
        info = stage_a(name, src, comp, device, adapted, epochs=a.stage_a_epochs)
        notes.append(f"- {name}: stage A trained on {info['train']} complaints, held-out disease accuracy {info['val_disease_acc']:.3f} ({info['classes']} diseases)")
        for variant, path in (("base", src), ("adapted", str(adapted))):
            mid = name if variant == "base" else f"{name}-mlt"
            X = base.embed_frozen(mid, gold["text"].tolist(), device, path)
            p, _ = base.lofo_frozen(gold, X)
            rows.append({"encoder": name, "variant": variant, "mode": "frozen", "seed": 0, **cv.score(y, p.tolist())})
            if not a.skip_finetune:
                for seed in range(a.seeds):
                    p, _ = base.lofo_finetune(gold, mid, device, seed, path=path, emergency_weight=a.emergency_weight)
                    rows.append({"encoder": name, "variant": variant, "mode": "finetune", "seed": seed, **cv.score(y, p.tolist())})
            print(f"   {variant} done ({time.time() - t0:.0f}s)")
    res = pd.DataFrame(rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    res.to_csv(RESULTS_DIR / "gpu_multilingual_results.csv", index=False)
    import platform, torch, transformers
    (RESULTS_DIR / "gpu_run_info.json").write_text(json.dumps({
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"), "device": torch.cuda.get_device_name(device) if device.startswith("cuda") else device,
        "torch": torch.__version__, "transformers": transformers.__version__, "python": platform.python_version(), "os": platform.platform(),
        "args": vars(a), "gold_texts": int(len(gold)), "external_complaints": int(len(comp)), "adapted_weights_dir": str(ADAPTED_DIR),
        "recipe": {"stage_a": {"epochs": a.stage_a_epochs, "lr": 2e-5, "batch": 32, "max_len": 64, "head": "linear on mean-pool, 10 disease classes"},
                   "stage_b_finetune": {"epochs": 12, "lr": 3e-5, "batch": 16, "emergency_weight": a.emergency_weight}}}, indent=1), encoding="utf-8")
    keep = [c for c in ("macro_f1", "accuracy", "emergency_recall", "over_triage") if c in res.columns]
    agg = res.groupby(["encoder", "variant", "mode"])[keep].mean().round(3).reset_index()
    verdict = []
    for name in a.models:
        for mode in sorted(res["mode"].unique()):
            b = agg[(agg.encoder == name) & (agg.variant == "base") & (agg["mode"] == mode)]
            ad = agg[(agg.encoder == name) & (agg.variant == "adapted") & (agg["mode"] == mode)]
            if len(b) and len(ad):
                ok = ad.macro_f1.iloc[0] > b.macro_f1.iloc[0] and ad.emergency_recall.iloc[0] >= b.emergency_recall.iloc[0]
                verdict.append(f"- {name} / {mode}: adapted F1 {ad.macro_f1.iloc[0]} vs base {b.macro_f1.iloc[0]}; recall {ad.emergency_recall.iloc[0]} vs {b.emergency_recall.iloc[0]} -> **{'ADOPT' if ok else 'keep base'}**")
    table = "| " + " | ".join(agg.columns) + " |\n|" + "---|" * len(agg.columns) + "\n" + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in agg.itertuples(index=False))
    report = ["# 10 — GPU run: multilingual adaptation then CareCompass LOFO", "", *notes, "", "Means over seeds; LOFO over 66 texts / 20 families.", "", table, "", "## Decision rule", "", *verdict, ""]
    report += ["## What to do with this", "",
               "1. Commit `pipeline/results/` and this report (small). Do NOT commit `pipeline/models_ft/` (weights).",
               "2. Per the decision rule above, an ADOPT row means the adapted encoder is better on the 66-text LOFO. The deployment plan has no model weights at runtime, so use this only as a yardstick for the rules layer (see progress.md section 0).",
               "3. Paste `pipeline/results/gpu_run_info.json` and this table into the next session so the assistant can update progress.md.", ""]
    (REPORTS_DIR / "10_gpu_multilingual.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
