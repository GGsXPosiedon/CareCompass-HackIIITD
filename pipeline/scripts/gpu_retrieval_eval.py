"""Stage 7a: retrieval baselines (BM25 / dense / RRF-hybrid kNN) with the SAME encoder on corpus and query.

  python scripts/gpu_retrieval_eval.py --gpu-name 4060 --models-dir ..\\models
  python scripts/gpu_retrieval_eval.py --dry-run          # hashed n-gram vectors, CPU only (checks the plumbing)

Corpus texts are embedded with the 'passage: ' prefix and queries with 'query: ' (e5 convention; other encoders get no
prefix). Evaluation is leave-one-family-out: the held-out text's whole scenario family is removed from the corpus.
Writes reports/07_retrieval.md and data/processed/retrieval_*.csv."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import gpu_encoder_eval as G  # noqa: E402
from ccpipe.followup.select import next_question  # noqa: E402
from ccpipe.paths import PIPELINE_DIR, PROCESSED_DIR, REPORTS_DIR  # noqa: E402
from ccpipe.retrieval.evaluate import lofo_retrieval, report_rows  # noqa: E402
from ccpipe.triage.data import load_unique  # noqa: E402

DEFAULT_MODELS = ["intfloat/multilingual-e5-base"]


def embed_both(model_id, texts, device, path):
    from sentence_transformers import SentenceTransformer

    m = SentenceTransformer(path or model_id, device=device)
    e5 = "e5" in model_id.lower()
    q = m.encode([("query: " + t) if e5 else t for t in texts], normalize_embeddings=True, batch_size=32)
    p = m.encode([("passage: " + t) if e5 else t for t in texts], normalize_embeddings=True, batch_size=32)
    return q, p


def md_table(t: pd.DataFrame) -> str:
    t = t.round(3)
    rows = ["| " + " | ".join(t.columns) + " |", "|" + "---|" * len(t.columns)]
    rows += ["| " + " | ".join(str(v) for v in r) + " |" for r in t.itertuples(index=False)]
    return "\n".join(rows)


def followup_table() -> str:
    import yaml

    cases = yaml.safe_load((PIPELINE_DIR / "eval" / "followup_cases.yaml").read_text(encoding="utf-8"))
    rows = ["| id | message | first question asked | expected | ok |", "|---|---|---|---|---|"]
    for c in cases:
        q = next_question([c["text"]], [], c["lang"])
        got = q.id if q else None
        rows.append(f"| {c['id']} | {c['text']} | {got} | {c['first']} | {'yes' if got == c['first'] else 'NO'} |")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--models-dir", default=None)
    ap.add_argument("--gpu-name", default="4060")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    df = load_unique()
    texts = df["text"].tolist()
    sections, summary = [], []
    models = ["dry-run-hash"] if a.dry_run else a.models
    device = None if a.dry_run else G.pick_device(a.gpu_name)
    for mid in models:
        t0 = time.time()
        if a.dry_run:
            q = p = G.embed_dry(texts)
        else:
            q, p = embed_both(mid, texts, device, G._resolve(mid, a.models_dir))
        preds, _ = lofo_retrieval(df, q, p, k=a.k)
        tab = report_rows(df, preds)
        tab.insert(0, "encoder", mid)
        summary.append(tab)
        sections.append(f"### {mid}  ({time.time() - t0:.1f}s)\n\n{md_table(tab.drop(columns='encoder'))}")
    out = pd.concat(summary)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(PROCESSED_DIR / ("retrieval_dry.csv" if a.dry_run else "retrieval_results.csv"), index=False)
    md = ["# Stage 7a: retrieval baselines and follow-up bank", "",
          f"{len(df)} unique texts, {df['family'].nunique()} families, leave-one-family-out, k={a.k}. "
          "Classes: 5 care types + ask_followup. With this little data treat differences of a few points as noise.", "",
          "## Retrieval kNN routing", "", *sections, "",
          "## Follow-up question bank (rule selection, no model)", "", followup_table(), ""]
    (REPORTS_DIR / ("07_retrieval_dry.md" if a.dry_run else "07_retrieval.md")).write_text("\n".join(md), encoding="utf-8")
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
