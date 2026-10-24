"""DDXPlus -> CanonicalCase. Evidence tokens are decoded with a dictionary; never eval'd.

Unknown != absent: only evidence the patient record lists becomes a fact, always PRESENT.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ..schemas import (Assertion, CanonicalCase, Demographics, Fact, LanguageInfo, Origin, Provenance,
                       Review, ReviewStatus, Source, SourceLabels, Split)
from ..splits import parse_tokens

SPLIT_MAP = {"train": Split.TRAIN, "validate": Split.VAL, "test": Split.TEST}
_TOKEN = re.compile(r"^(E_\d+)(?:_@_(V_\d+|\d+))?$")


@dataclass
class DecodeStats:
    tokens: int = 0
    unresolved: Counter = field(default_factory=Counter)
    by_type: Counter = field(default_factory=Counter)
    explicit_no_not_modelled: int = 0


def load_evidences(ddx_dir: Path) -> dict:
    with open(ddx_dir / "release_evidences.json", encoding="utf-8") as fh:
        return json.load(fh)


def decode_evidence(tokens: list[str], evidences: dict, initial: str | None, stats: DecodeStats) -> list[Fact]:
    """Decode tokens into PRESENT facts. Multi-choice (M) tokens for one code are merged into one fact."""
    multi: dict[str, list[str]] = {}
    facts: list[Fact] = []
    for tok in tokens:
        stats.tokens += 1
        m = _TOKEN.match(tok)
        code = m.group(1) if m else None
        spec = evidences.get(code) if code else None
        if spec is None:
            stats.unresolved[tok.split("_@_")[0]] += 1
            continue
        dtype = spec["data_type"]
        stats.by_type[dtype] += 1
        value = m.group(2)
        if dtype == "B" and value is None:
            facts.append(Fact(concept_id=f"ddxplus:{code}", assertion=Assertion.PRESENT, value=True,
                              origin=Origin.DECODED_SOURCE_CODE, is_initial=(code == initial)))
        elif dtype == "C" and value is not None and value.isdigit():
            facts.append(Fact(concept_id=f"ddxplus:{code}", assertion=Assertion.PRESENT, value=int(value),
                              origin=Origin.DECODED_SOURCE_CODE, is_initial=(code == initial)))
        elif dtype == "C" and value is not None and value.startswith("V_"):
            label = spec["value_meaning"].get(value, {}).get("en")
            if label is None:
                stats.unresolved[tok] += 1
            elif label == "N":
                # Recorded "No" answer. The schema forbids ABSENT facts on DDXPlus, so it is counted, not emitted.
                stats.explicit_no_not_modelled += 1
            elif label == "Y":
                facts.append(Fact(concept_id=f"ddxplus:{code}", assertion=Assertion.PRESENT, value=True,
                                  origin=Origin.DECODED_SOURCE_CODE, is_initial=(code == initial)))
            else:
                facts.append(Fact(concept_id=f"ddxplus:{code}", assertion=Assertion.PRESENT, value=label,
                                  value_label=label, origin=Origin.DECODED_SOURCE_CODE,
                                  is_initial=(code == initial)))
        elif dtype == "M" and value is not None and value.startswith("V_"):
            label = spec["value_meaning"].get(value, {}).get("en")
            if label is None:
                stats.unresolved[tok] += 1
                continue
            multi.setdefault(code, []).append(label)
        else:
            stats.unresolved[tok] += 1
    for code, labels in multi.items():
        facts.append(Fact(concept_id=f"ddxplus:{code}", assertion=Assertion.PRESENT, value=sorted(labels),
                          origin=Origin.DECODED_SOURCE_CODE, is_initial=(code == initial)))
    return facts


def build_cases(path: Path, split: str, evidences: dict, drop: set[int], n_target: int,
                stats: DecodeStats) -> list[CanonicalCase]:
    """Deterministic sample: after removing duplicate rows, keep every k-th remaining row."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False,
                     usecols=["AGE", "SEX", "PATHOLOGY", "EVIDENCES", "INITIAL_EVIDENCE"])
    keep = df.index[~df.index.isin(drop)]
    step = max(1, len(keep) // n_target)
    chosen = keep[::step][:n_target]
    cases = []
    for idx in chosen:
        r = df.loc[idx]
        age = int(r["AGE"]) if r["AGE"].isdigit() else None
        cases.append(CanonicalCase(
            case_id=f"ddxplus:{split}:{idx}", source=Source.DDXPLUS, source_split=split,
            scenario_group_id=f"ddx:{split}:{idx}", split=SPLIT_MAP[split],
            language=LanguageInfo(declared="English", script="latin"),
            facts=decode_evidence(parse_tokens(r["EVIDENCES"]), evidences, r["INITIAL_EVIDENCE"] or None, stats),
            demographics=Demographics(age_years=age, sex_reported=r["SEX"] or None),
            source_labels=SourceLabels(pathology=r["PATHOLOGY"] or None),
            review=Review(clinical_review_status=ReviewStatus.UNREVIEWED),
            provenance=Provenance(source_row_id=str(idx), source_file=path.name, generation_method="simulated"),
        ))
    return cases
