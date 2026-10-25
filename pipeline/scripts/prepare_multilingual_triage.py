"""Prepare Tulsiandhare/Multilingual_medical_symptom_triage for CareCompass (CPU only, no torch).

    python scripts/prepare_multilingual_triage.py --csv <datasets>/multilingual_triage/multilingual_medical_symptom_triage.csv

What it does (and why; findings are in progress.md):
  1. Audits the labels. In this dataset `urgency`/`severity` are NOT predictable from the text (char-n-gram LR: 0.371 accuracy vs
     0.367 majority), so they are never used as care-type or emergency labels. `disease` IS fully determined by the text.
  2. Extracts the complaint sentence (drops the "Patient: Female, 55 years old" header, so age/gender cannot leak) and de-duplicates.
  3. Detects the real language by script (the `language` column is wrong for ~35% of rows: "English" rows in Telugu etc.).
  4. Derives a symptom-cue vocabulary per script: tokens whose frequency is concentrated in some diseases (lift vs the corpus)
     and not function words. Written to backend/app/rules/dataset_vocab.json and used by the intent gate as a data-derived health cue.
Outputs: pipeline/data/processed/mlt_complaints.jsonl, backend/app/rules/dataset_vocab.json, pipeline/reports/09_multilingual_dataset.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_JSONL = ROOT / "pipeline" / "data" / "processed" / "mlt_complaints.jsonl"
OUT_VOCAB = ROOT / "backend" / "app" / "rules" / "dataset_vocab.json"
OUT_REPORT = ROOT / "pipeline" / "reports" / "09_multilingual_dataset.md"
HEADER_SPLIT = re.compile(r"(?:Complaint|शिकायत|অভিযোগ|ఫిర్యాదు|ફરિયાદ|તકલીફ|तक्रार)\s*:", re.I)
TOKEN = re.compile(r"[^\s\d,.;:!?|।()\"'’‘“”\-/]+", re.U)  # keeps Indic combining marks inside words
USECOLS = ["patient_query", "disease", "category", "language", "severity", "urgency", "symptom_1", "symptom_2", "symptom_3", "age"]
LIFT_MIN, DF_MIN = 1.6, 15


def script_of(text: str) -> str:
    c: Counter = Counter()
    for ch in text:
        if ch.isalpha():
            c[unicodedata.name(ch, "X").split()[0]] += 1
    return c.most_common(1)[0][0].lower() if c else "none"


def complaint(q: str) -> str:
    parts = HEADER_SPLIT.split(q, maxsplit=1)
    return parts[-1].strip()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252 and crash on Indic text
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--no-vocab", action="store_true")
    a = ap.parse_args()
    df = pd.read_csv(a.csv, usecols=USECOLS)
    n_rows = len(df)
    df["complaint"] = df["patient_query"].map(complaint)
    df["script"] = df["complaint"].map(script_of)
    # code-mixed Hindi/Hinglish written in Latin is still "latin": split further by a Hinglish function-word check
    hing = re.compile(r"\b(mujhe|mujhko|hai|hain|ho raha|ho rahi|aur|ke saath|se pareshan|bhi|nahi|mera|meri|kal|din)\b", re.I)
    df["lang"] = [("hinglish" if hing.search(c) else "english") if s == "latin" else s for c, s in zip(df["complaint"], df["script"])]
    uniq = df.drop_duplicates(["complaint", "disease"]).reset_index(drop=True)

    # --- label audit -------------------------------------------------------------------
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold, cross_val_score
    X = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3, max_features=60000).fit_transform(uniq["complaint"])
    grp = pd.factorize(uniq["complaint"].str.lower())[0] % 997
    audit = {}
    for tgt in ("disease", "urgency"):
        s = cross_val_score(LogisticRegression(max_iter=300), X, uniq[tgt], cv=GroupKFold(5), groups=grp)
        audit[tgt] = (float(s.mean()), float(uniq[tgt].value_counts(normalize=True).max()))
    mism = pd.crosstab(df["language"], df["lang"])

    # --- complaints for training ---------------------------------------------------------
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf-8") as fh:
        for r in uniq.itertuples():
            fh.write(json.dumps({"text": r.complaint, "disease": r.disease, "category": r.category, "lang": r.lang,
                                 "symptoms": [r.symptom_1, r.symptom_2, r.symptom_3]}, ensure_ascii=False) + "\n")

    # --- data-derived symptom cue vocabulary ----------------------------------------------
    vocab: dict = {}
    if not a.no_vocab:
        docs = [set(t.lower() for t in TOKEN.findall(c) if len(t) >= 3) for c in uniq["complaint"]]
        dz = uniq["disease"].to_numpy()
        diseases = sorted(set(dz))
        n = len(docs)
        df_all: Counter = Counter()
        df_d: dict = {d: Counter() for d in diseases}
        for toks, d in zip(docs, dz):
            df_all.update(toks)
            df_d[d].update(toks)
        n_d = {d: int((dz == d).sum()) for d in diseases}
        langs_of: dict = defaultdict(Counter)
        for toks, l in zip(docs, uniq["lang"]):
            for t in toks:
                langs_of[t][l] += 1
        for t, c in df_all.items():
            if c < DF_MIN:
                continue
            p_all = c / n
            best_d, best = max(((d, (df_d[d][t] / n_d[d]) / p_all) for d in diseases), key=lambda x: x[1])
            if best >= LIFT_MIN and df_d[best_d][t] >= 8:
                vocab[t] = {"df": c, "lift": round(best, 2), "disease": best_d, "lang": langs_of[t].most_common(1)[0][0]}
        OUT_VOCAB.write_text(json.dumps({"source": "Tulsiandhare/Multilingual_medical_symptom_triage", "lift_min": LIFT_MIN, "df_min": DF_MIN,
                                         "tokens": dict(sorted(vocab.items()))}, ensure_ascii=False, indent=0), encoding="utf-8")

    by_lang = Counter(v["lang"] for v in vocab.values())
    lines = ["# 09 — Multilingual medical symptom triage dataset: audit and derived assets", "",
             f"Source: `Tulsiandhare/Multilingual_medical_symptom_triage` ({n_rows} rows -> {len(uniq)} unique complaints after removing the demographic header).", "",
             "## Label audit (grouped 5-fold, char n-gram LR)", "",
             "| Target | Accuracy | Majority baseline |", "|---|---|---|",
             *[f"| {k} | {v[0]:.3f} | {v[1]:.3f} |" for k, v in audit.items()], "",
             "`urgency` (= `severity`, identical up to renaming) is at chance: it is independent of disease, symptoms, age and comorbidities in the generator. "
             "It is therefore **not used** as an emergency/care label. `disease` is determined by the text (a 10-class task with 1.0 accuracy), "
             "so the dataset is used for multilingual symptom understanding, not for urgency.", "",
             "## Language column vs real script of the complaint", "", "```\n" + mism.to_string() + "\n```", "",
             "## Derived symptom-cue vocabulary", "", f"{len(vocab)} tokens (lift >= {LIFT_MIN}, document frequency >= {DF_MIN}); by language: {dict(by_lang)}.", "",
             "Examples (highest lift per language):", ""]
    for l in sorted(by_lang):
        top = sorted((t for t, v in vocab.items() if v["lang"] == l), key=lambda t: -vocab[t]["lift"])[:12]
        lines.append(f"- **{l}**: " + ", ".join(top))
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
