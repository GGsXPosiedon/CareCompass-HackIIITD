"""Stage 3: build canonical files and the harmonization report."""
from __future__ import annotations

import json
from collections import Counter

import pandas as pd

from .adapters import carecompass, caregivers, ddxplus, synapse
from .families import load_family_table
from .paths import CONFIG_DIR, PROCESSED_DIR, REPORTS_DIR, SPLITS_DIR, data_file
from .taxonomy import load_label_adapter

DDX_SAMPLE_PER_SPLIT = 2000


def _dump(path, items) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for item in items:
            fh.write(item.model_dump_json() + "\n")


def run_harmonize() -> dict:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    adapter = load_label_adapter()
    table = load_family_table(CONFIG_DIR / "scenario_families.yaml")
    summary: dict = {"mapping_version": adapter.mapping_version}

    cc_df = pd.read_csv(data_file("carecompass_csv"), dtype=str, keep_default_na=False)
    cc = carecompass.build_cases(cc_df, table, adapter)
    assert len(cc) == len(cc_df)
    _dump(PROCESSED_DIR / "carecompass.jsonl", cc)
    summary["carecompass"] = {
        "rows_in": len(cc_df), "cases_out": len(cc),
        "flags": dict(Counter(f for c in cc for f in c.quality_flags)),
        "empty_cells": {c: int((cc_df[c] == "").sum()) for c in cc_df.columns if (cc_df[c] == "").any()},
    }

    cg_df = pd.read_csv(data_file("caregivers"), dtype=str, keep_default_na=False)
    cg = caregivers.build_caregivers(cg_df)
    with open(PROCESSED_DIR / "caregivers.jsonl", "w", encoding="utf-8") as fh:
        for c in cg:
            fh.write(c.model_dump_json() + "\n")
    summary["caregivers"] = {"rows_in": len(cg_df), "out": len(cg), "inactive": sum(not c.active for c in cg)}

    syn_df = pd.read_csv(data_file("synapse"), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    gs = pd.read_csv(SPLITS_DIR / "synapse_group_split.csv", dtype=str)
    syn = synapse.build_cases(syn_df, dict(zip(gs["group_id"], gs["split"])))
    assert len(syn) == len(syn_df)
    _dump(PROCESSED_DIR / "synapse.jsonl", syn)
    summary["synapse"] = {"rows_in": len(syn_df), "cases_out": len(syn),
                          "splits": dict(Counter(c.split.value for c in syn))}

    ddx_dir = data_file("ddx_dir")
    evidences = ddxplus.load_evidences(ddx_dir)
    stats = ddxplus.DecodeStats()
    ddx_cases = []
    for split in ("train", "validate", "test"):
        drop_file = SPLITS_DIR / f"ddx_drop_indices_{split}.txt"
        drop = {int(x) for x in drop_file.read_text().split()}
        ddx_cases += ddxplus.build_cases(ddx_dir / f"release_{split}_patients.csv", split, evidences,
                                         drop, DDX_SAMPLE_PER_SPLIT, stats)
    _dump(PROCESSED_DIR / "ddxplus_sample.jsonl", ddx_cases)
    summary["ddxplus"] = {"cases_out": len(ddx_cases), "tokens": stats.tokens,
                          "unresolved_tokens": sum(stats.unresolved.values()),
                          "unresolved_top": stats.unresolved.most_common(5),
                          "by_type": dict(stats.by_type), "explicit_no_not_modelled": stats.explicit_no_not_modelled,
                          "absent_facts": sum(f.assertion.value == "absent" for c in ddx_cases for f in c.facts)}

    (PROCESSED_DIR / "harmonize_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = ["# 03 — Harmonization", "",
             f"Label mapping: `{adapter.mapping_version}` (interim team decision, not organizer-approved).", "",
             "| Source | Rows in | Cases out | Notes |", "|---|---:|---:|---|",
             f"| CareCompass | {summary['carecompass']['rows_in']} | {summary['carecompass']['cases_out']} | "
             f"flags {summary['carecompass']['flags']}; empty cells {summary['carecompass']['empty_cells']} |",
             f"| Caregivers | {summary['caregivers']['rows_in']} | {summary['caregivers']['out']} | "
             f"inactive {summary['caregivers']['inactive']} |",
             f"| SYNAPSE | {summary['synapse']['rows_in']} | {summary['synapse']['cases_out']} | "
             f"splits {summary['synapse']['splits']}; severity/recommendation kept as source labels only |",
             f"| DDXPlus (sample) | – | {summary['ddxplus']['cases_out']} | "
             f"{DDX_SAMPLE_PER_SPLIT}/split after dedupe; tokens {stats.tokens:,}, unresolved "
             f"{summary['ddxplus']['unresolved_tokens']}, recorded-No answers not modelled {stats.explicit_no_not_modelled}, absent facts {summary['ddxplus']['absent_facts']} |",
             "", "Outputs are in `data/processed/` (git-ignored; regenerate with `python -m ccpipe.cli harmonize`).",
             "Red flags from the CSV are kept verbatim in `source_labels.red_flags_raw`, flagged "
             "`red_flags_quarantined_unreviewed`, and never copied into `approved_labels`.", ""]
    (REPORTS_DIR / "03_harmonization.md").write_text("\n".join(lines), encoding="utf-8")
    return summary
