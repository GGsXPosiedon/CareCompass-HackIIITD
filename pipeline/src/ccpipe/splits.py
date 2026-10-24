"""Stage 1: leakage-safe splits.

CareCompass: 3 grouped folds over frozen scenario families.
SYNAPSE: group by normalised Symptoms text, then assign groups to train/val/test by seeded hash.
DDXPlus: keep the official split identity; drop exact-duplicate patient signatures, giving test priority.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from .families import FamilyTable, load_family_table, validate_table
from .paths import CONFIG_DIR, REPORTS_DIR, SPLITS_DIR, data_file
from .textutil import normalize_text

# ---------------------------------------------------------------- CareCompass


def assign_carecompass_folds(df: pd.DataFrame, table: FamilyTable) -> pd.DataFrame:
    out = df.copy()
    out["family_id"] = [table.family_of(u) for u in out["user_input"]]
    out["fold"] = [table.fold_of(f) for f in out["family_id"]]
    return out


def check_carecompass_leakage(df: pd.DataFrame) -> list[str]:
    """Return a list of problems; an empty list means the folds are leakage-safe."""
    problems: list[str] = []
    if df["fold"].isna().any():
        problems.append("some rows have no fold")
    multi_fam = df.groupby("family_id")["fold"].nunique()
    if (multi_fam > 1).any():
        problems.append(f"families split across folds: {list(multi_fam[multi_fam > 1].index)}")
    multi_utt = df.groupby("user_input")["fold"].nunique()
    if (multi_utt > 1).any():
        problems.append(f"{int((multi_utt > 1).sum())} utterances appear in more than one fold")
    labelled = df[df["care_type"] != ""]
    all_types = set(labelled["care_type"])
    for fold, part in labelled.groupby("fold"):
        missing = all_types - set(part["care_type"])
        if missing:
            problems.append(f"fold {fold} has no {sorted(missing)} case")
    return problems


def fold_summary(df: pd.DataFrame) -> pd.DataFrame:
    labelled = df.assign(care_type=df["care_type"].replace("", "<follow-up>"))
    return (
        labelled.groupby(["fold", "care_type"])
        .agg(families=("family_id", "nunique"), utterances=("user_input", "nunique"), rows=("id", "count"))
        .reset_index()
    )


# -------------------------------------------------------------------- SYNAPSE

SYNAPSE_SEED = "cc-synapse-v1"


def normalize_symptoms(text: str) -> str:
    return normalize_text(text).lower()


def symptom_group_id(normalized: str) -> str:
    return hashlib.blake2b(normalized.encode("utf-8"), digest_size=6).hexdigest()


def assign_group_split(group_id: str, seed: str = SYNAPSE_SEED) -> str:
    bucket = int(hashlib.blake2b(f"{seed}:{group_id}".encode(), digest_size=8).hexdigest(), 16) % 1000
    if bucket < 800:
        return "train"
    return "val" if bucket < 900 else "test"


def build_synapse_split_table(symptoms: pd.Series) -> pd.DataFrame:
    normalized = symptoms.map(normalize_symptoms)
    counts = normalized.value_counts()
    table = pd.DataFrame({"normalized_symptoms": counts.index, "n_rows": counts.values})
    table["group_id"] = table["normalized_symptoms"].map(symptom_group_id)
    table["split"] = table["group_id"].map(assign_group_split)
    if table["group_id"].duplicated().any():
        raise ValueError("hash collision between distinct symptom strings")
    return table[["group_id", "split", "n_rows", "normalized_symptoms"]].sort_values("group_id")


# -------------------------------------------------------------------- DDXPlus

_TOKEN = re.compile(r"'([^']*)'")


def parse_tokens(evidences: str) -> list[str]:
    return _TOKEN.findall(evidences)


def patient_signature(age: str, sex: str, pathology: str, tokens: list[str]) -> int:
    key = "|".join([age, sex, pathology, ",".join(sorted(tokens))])
    return int.from_bytes(hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest(), "big")


DDX_PRIORITY = ("test", "validate", "train")  # earlier splits are never contaminated by later ones


def ddx_dedupe_plan(ddx_dir: Path) -> dict[str, dict]:
    seen: dict[str, set[int]] = {s: set() for s in DDX_PRIORITY}
    plan: dict[str, dict] = {}
    for i, split in enumerate(DDX_PRIORITY):
        earlier = DDX_PRIORITY[:i]
        drops_within: list[int] = []
        drops_cross: list[int] = []
        index = 0
        path = ddx_dir / f"release_{split}_patients.csv"
        for chunk in pd.read_csv(path, dtype=str, keep_default_na=False, chunksize=200_000,
                                 usecols=["AGE", "SEX", "PATHOLOGY", "EVIDENCES"]):
            for age, sex, patho, evs in zip(chunk["AGE"], chunk["SEX"], chunk["PATHOLOGY"], chunk["EVIDENCES"]):
                sig = patient_signature(age, sex, patho, parse_tokens(evs))
                if sig in seen[split]:
                    drops_within.append(index)
                elif any(sig in seen[e] for e in earlier):
                    drops_cross.append(index)
                else:
                    seen[split].add(sig)
                index += 1
        plan[split] = {
            "rows": index,
            "dropped_within_split": sorted(drops_within),
            "dropped_cross_split": sorted(drops_cross),
        }
    return plan


# ----------------------------------------------------------------- orchestration


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def run_splits(skip_ddx: bool = False) -> dict:
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary: dict = {}

    table = load_family_table(CONFIG_DIR / "scenario_families.yaml")
    cc = pd.read_csv(data_file("carecompass_csv"), dtype=str, keep_default_na=False)
    validate_table(table, cc["user_input"].unique())
    cc = assign_carecompass_folds(cc, table)
    problems = check_carecompass_leakage(cc)
    cc[["id", "family_id", "fold", "care_type", "detected_language"]].to_csv(
        SPLITS_DIR / "carecompass_folds.csv", index=False, encoding="utf-8"
    )
    summary["carecompass"] = {"rows": len(cc), "families": len(table.families), "problems": problems}

    syn = pd.read_csv(data_file("synapse"), dtype=str, keep_default_na=False, usecols=["Symptoms"],
                      encoding="utf-8-sig")
    syn_table = build_synapse_split_table(syn["Symptoms"])
    syn_table.to_csv(SPLITS_DIR / "synapse_group_split.csv", index=False, encoding="utf-8")
    per_split_rows = syn_table.groupby("split")["n_rows"].sum().to_dict()
    per_split_groups = syn_table.groupby("split").size().to_dict()
    summary["synapse"] = {"rows": int(len(syn)), "groups": int(len(syn_table)),
                          "rows_per_split": {k: int(v) for k, v in per_split_rows.items()},
                          "groups_per_split": {k: int(v) for k, v in per_split_groups.items()}}

    if not skip_ddx:
        plan = ddx_dedupe_plan(data_file("ddx_dir"))
        ddx_summary = {}
        for split, info in plan.items():
            drops = sorted(info["dropped_within_split"] + info["dropped_cross_split"])
            (SPLITS_DIR / f"ddx_drop_indices_{split}.txt").write_text(
                "\n".join(map(str, drops)) + ("\n" if drops else ""), encoding="utf-8")
            ddx_summary[split] = {
                "rows": info["rows"],
                "dropped_within_split": len(info["dropped_within_split"]),
                "dropped_cross_split": len(info["dropped_cross_split"]),
                "kept": info["rows"] - len(drops),
            }
        summary["ddxplus"] = ddx_summary
    (SPLITS_DIR / "split_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = ["# 01 — Leakage-safe splits", "",
             "## CareCompass: 3 grouped folds over 20 frozen scenario families", "",
             _md_table(fold_summary(cc)), "",
             f"Leakage check: {'**PASS**' if not problems else '**FAIL** — ' + '; '.join(problems)}", "",
             "Reading these numbers: each fold's test scenarios are *unseen scenarios in all three languages*. "
             "Each fold has one emergency family, so emergency recall can only be read per scenario. "
             "Use the folds as regression tests, not as evidence of clinical safety.", "",
             "## SYNAPSE: grouped by normalised `Symptoms` text", "",
             f"{summary['synapse']['groups']:,} groups, {summary['synapse']['rows']:,} rows. "
             f"Rows per split: {summary['synapse']['rows_per_split']}; groups per split: "
             f"{summary['synapse']['groups_per_split']}. Severity is not used (no signal; see DATA_AUDIT §5.1).", ""]
    if not skip_ddx:
        lines += ["## DDXPlus: duplicate patient signatures removed (priority test > validate > train)", "",
                  _md_table(pd.DataFrame(summary["ddxplus"]).T.reset_index(names="split")), ""]
    (REPORTS_DIR / "01_splits.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary
