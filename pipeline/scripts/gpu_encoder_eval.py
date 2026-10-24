"""Pretrained-encoder track for Stage 6 (run on a machine with a GPU and Hugging Face access).

Same data, same families and same leave-one-family-out (LOFO) protocol as reports/06_triage.md, so numbers are
directly comparable. Nothing here is tuned on the held-out family: fine-tuning uses a fixed recipe and fixed epochs.

  pip install torch transformers sentence-transformers scikit-learn pandas pyyaml pydantic indic-transliteration
  cd pipeline && export PYTHONPATH=src CC_DATA_DIR=/path/to/datasets
  python scripts/gpu_encoder_eval.py --mode frozen --models intfloat/multilingual-e5-base BAAI/bge-m3
  python scripts/gpu_encoder_eval.py --mode finetune --models google/muril-base-cased xlm-roberta-base --seeds 3
  python scripts/gpu_encoder_eval.py --mode frozen --dry-run        # checks the plumbing with no torch / no downloads

STATUS: written but NOT executed in the build workspace (no GPU, no Hugging Face access there). Verify model ids on
their model cards before relying on them (the 2026 small models mentioned in benchmarks, e.g. harrier-oss-v1 or
granite-embedding-multilingual-r2, can be passed with --models once you have confirmed the exact repo id).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from ccpipe.paths import PROCESSED_DIR, REPORTS_DIR
from ccpipe.triage import cv
from ccpipe.triage.data import CLASSES, load_unique

FROZEN_MODELS = ["intfloat/multilingual-e5-base", "intfloat/multilingual-e5-large", "BAAI/bge-m3",
                 "google/muril-base-cased", "xlm-roberta-base", "Qwen/Qwen3-Embedding-0.6B"]
# Full fine-tuning keeps fp32 AdamW state (~16 bytes/param): base-size models fit an 8 GB RTX 4060, large ones do not.
FINETUNE_MODELS = ["intfloat/multilingual-e5-base", "google/muril-base-cased", "xlm-roberta-base"]
MAX_FT_PARAMS = 300_000_000
LABEL_ID = {c: i for i, c in enumerate(CLASSES)}


def pick_device(name_hint: str) -> str:
    """Select the NVIDIA GPU by name (e.g. '4060'). Refuses to fall back to another device or the CPU."""
    import torch

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available to PyTorch (install the CUDA build of torch and an NVIDIA driver).")
    names = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    for i, n in enumerate(names):
        if name_hint.lower() in n.lower():
            print(f"using cuda:{i} = {n}")
            return f"cuda:{i}"
    raise SystemExit(f"No CUDA device matching {name_hint!r}; PyTorch sees: {names}")


def _resolve(model_id: str, models_dir: str | None) -> str:
    """Local folder for a manually downloaded model (no network); otherwise the hub id."""
    if not models_dir:
        return model_id
    path = Path(models_dir) / model_id.split("/")[-1]
    if not (path / "config.json").exists():
        raise SystemExit(f"{path} missing config.json: download {model_id} into it first")
    return str(path)


def _prefix(model_id: str, text: str) -> str:
    return f"query: {text}" if "e5" in model_id.lower() else text


def embed_dry(texts):
    out = np.zeros((len(texts), 256))
    for i, t in enumerate(texts):
        t = f" {t.lower()} "
        for n in (2, 3, 4):
            for j in range(len(t) - n + 1):
                out[i, int(hashlib.md5(t[j:j + n].encode()).hexdigest(), 16) % 256] += 1
    return out / np.linalg.norm(out, axis=1, keepdims=True).clip(1e-9)


def embed_frozen(model_id: str, texts, device: str, path: str | None = None):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(path or model_id, device=device)
    return model.encode([_prefix(model_id, t) for t in texts], normalize_embeddings=True, batch_size=32)


def _aligned(clf, proba: np.ndarray) -> np.ndarray:
    out = np.zeros((proba.shape[0], len(CLASSES)))
    for j, c in enumerate(clf.classes_):
        out[:, CLASSES.index(c)] = proba[:, j]
    return out


def lofo_frozen(df: pd.DataFrame, X: np.ndarray):
    """LR on frozen embeddings; C picked by an inner LOFO over training families (nested)."""
    groups = df["family"].to_numpy()
    y = df["label"].to_numpy()
    pred = np.empty(len(df), dtype=object)
    probs = np.zeros((len(df), len(CLASSES)))
    for fam in sorted(set(groups)):
        te = groups == fam
        tr_idx = np.where(~te)[0]
        best_c, best_key = 1.0, None
        for c in (0.3, 1.0, 10.0, 100.0):
            inner = np.empty(len(tr_idx), dtype=object)
            g_in = groups[tr_idx]
            for f2 in sorted(set(g_in)):
                m = g_in == f2
                clf = LogisticRegression(C=c, class_weight="balanced", max_iter=3000).fit(X[tr_idx][~m], y[tr_idx][~m])
                inner[m] = clf.predict(X[tr_idx][m])
            s = cv.score(y[tr_idx].tolist(), inner.tolist())
            key = (round(s["emergency_recall"], 6), round(s["macro_f1"], 6))
            if best_key is None or key > best_key:
                best_c, best_key = c, key
        clf = LogisticRegression(C=best_c, class_weight="balanced", max_iter=3000).fit(X[tr_idx], y[tr_idx])
        pred[te] = clf.predict(X[te])
        probs[te] = _aligned(clf, clf.predict_proba(X[te]))
    return pred, probs


def lofo_finetune(df: pd.DataFrame, model_id: str, device: str, seed: int, epochs: int = 12, lr: float = 3e-5,
                  path: str | None = None, emergency_weight: float = 3.0):
    """Cost-sensitive fine-tune: class-balanced weights, with the emergency class multiplied by `emergency_weight`
    so a missed emergency costs more than a false alarm. Returns (labels, probabilities)."""
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

    src_path = path or model_id
    tok = AutoTokenizer.from_pretrained(src_path)
    groups = df["family"].to_numpy()
    texts = [_prefix(model_id, t) for t in df["text"]]
    labels = torch.tensor([LABEL_ID[l] for l in df["label"]])
    pred = np.empty(len(df), dtype=object)
    probs = np.zeros((len(df), len(CLASSES)))

    def encode(idx):
        return tok([texts[i] for i in idx], padding=True, truncation=True, max_length=64, return_tensors="pt")

    for fam in sorted(set(groups)):
        torch.manual_seed(seed); np.random.seed(seed)
        te = np.where(groups == fam)[0]
        tr = np.where(groups != fam)[0]
        enc = AutoModel.from_pretrained(src_path).to(device)
        head = nn.Linear(enc.config.hidden_size, len(CLASSES)).to(device)
        counts = np.bincount(labels[tr].numpy(), minlength=len(CLASSES)).clip(1)
        w = len(tr) / (len(CLASSES) * counts)
        w[CLASSES.index("emergency_112")] *= emergency_weight
        weight = torch.tensor(w, dtype=torch.float, device=device)
        opt = torch.optim.AdamW(list(enc.parameters()) + list(head.parameters()), lr=lr, weight_decay=0.01)
        steps = epochs * int(np.ceil(len(tr) / 16))
        sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
        loss_fn = nn.CrossEntropyLoss(weight=weight)

        def forward(idx):
            b = {k: v.to(device) for k, v in encode(idx).items()}
            h = enc(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1)
            return head((h * m).sum(1) / m.sum(1))

        enc.train()
        for _ in range(epochs):
            order = np.random.permutation(tr)
            for s in range(0, len(order), 16):
                idx = order[s:s + 16]
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device.startswith("cuda")):
                    loss = loss_fn(forward(idx).float(), labels[idx].to(device))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(enc.parameters(), 1.0)
                opt.step(); sched.step(); opt.zero_grad()
        enc.eval()
        with torch.no_grad():
            logits = forward(te).float()
            probs[te] = torch.softmax(logits, -1).cpu().numpy()
            pred[te] = [CLASSES[i] for i in logits.argmax(-1).cpu().tolist()]
        del enc, head, opt
        if device.startswith("cuda"):
            torch.cuda.empty_cache()
    return pred, probs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["frozen", "finetune"], default="frozen")
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--models-dir", default=None, help="folder holding manually downloaded models, one sub-folder per repo name (e.g. models/multilingual-e5-base)")
    ap.add_argument("--gpu-name", default="4060", help="substring of the CUDA device name to use")
    ap.add_argument("--emergency-weight", type=float, default=3.0, help="extra loss multiplier on the emergency class (fine-tune)")
    ap.add_argument("--force-large", action="store_true", help="allow fine-tuning models above 300M parameters")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    df = load_unique()
    y = df["label"].tolist()
    device = "cpu" if args.dry_run else pick_device(args.gpu_name)
    models = args.models or (FINETUNE_MODELS if args.mode == "finetune" else FROZEN_MODELS)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    rows, preds = [], {}
    for model_id in (["dry-run-hash"] if args.dry_run else models):
        t0 = time.time()
        if args.mode == "frozen":
            X = embed_dry(df["text"].tolist()) if args.dry_run else embed_frozen(model_id, df["text"].tolist(), device, _resolve(model_id, args.models_dir))
            runs = [lofo_frozen(df, X)]
        else:
            from transformers import AutoModel
            local = _resolve(model_id, args.models_dir)
            n_params = sum(p.numel() for p in AutoModel.from_pretrained(local).parameters())
            if n_params > MAX_FT_PARAMS and not args.force_large:
                print(f"skip {model_id}: {n_params/1e6:.0f}M params > 300M (use --force-large, or frozen mode)")
                continue
            runs = [lofo_finetune(df, model_id, device, seed, path=local, emergency_weight=args.emergency_weight) for seed in range(args.seeds)]
        for seed, (p, pr) in enumerate(runs):
            s = cv.score(y, p.tolist())
            ci = cv.cluster_bootstrap(df, p)
            rows.append({"model": model_id, "mode": args.mode, "seed": seed, **s,
                         "macro_f1_ci": f"{ci['macro_f1'][0]:.2f}-{ci['macro_f1'][1]:.2f}", "seconds": round(time.time() - t0)})
            preds[f"{model_id}|{seed}"] = p.tolist()
            np.save(PROCESSED_DIR / f"probs_{args.mode}{'_dry' if args.dry_run else ''}_{model_id.split('/')[-1]}_s{seed}.npy", pr)
        print(model_id, rows[-1])
    if not rows:
        raise SystemExit("nothing was evaluated")
    out = pd.DataFrame(rows)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{args.mode}{'_dry' if args.dry_run else ''}"
    out.to_csv(PROCESSED_DIR / f"triage_encoders_{tag}.csv", index=False)
    (PROCESSED_DIR / f"triage_encoders_{tag}_preds.json").write_text(json.dumps(preds), encoding="utf-8")
    if not args.dry_run:
        lines = ["# 06b — Pretrained encoders (LOFO, same protocol as 06_triage.md)", "", "\n".join(["| " + " | ".join(out.columns) + " |", "|" + "---|" * len(out.columns)] + ["| " + " | ".join(str(v) for v in r) + " |" for r in out.itertuples(index=False)]), ""]
        (REPORTS_DIR / f"06b_encoders_{args.mode}.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
