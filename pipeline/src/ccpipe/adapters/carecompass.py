"""CareCompass CSV -> CanonicalCase. Pure and deterministic."""
from __future__ import annotations

import pandas as pd

from ..families import FamilyTable
from ..schemas import (ApprovedLabels, CanonicalCase, Demographics, LanguageInfo, Provenance,
                       RequestContext, Review, ReviewStatus, Source, SourceLabels, Split, Utterance)
from ..taxonomy import LabelAdapter
from ..textutil import detect_script, normalize_text

SOURCE_FILE = "triage_dataset_flat.csv"
FOLD_TO_SPLIT = {}  # CareCompass has no fixed train/test: folds are used for grouped CV only.
REFERENCE_FIELDS = ("reasoning", "follow_up_question", "matched_caregiver_ids", "top_score")


def _none(value: str) -> str | None:
    return value if value != "" else None


def build_cases(df: pd.DataFrame, table: FamilyTable, adapter: LabelAdapter) -> list[CanonicalCase]:
    cases: list[CanonicalCase] = []
    for row in df.to_dict("records"):
        care, urg = _none(row["care_type"]), _none(row["urgency"])
        flags: list[str] = []
        if care is None and urg is None:
            flags.append("no_routing_label_follow_up_expected")
        approved_care, approved_urg = adapter.approve("carecompass", care, urg)
        family = table.family_of(row["user_input"])
        red = _none(row["red_flags"])
        if red:
            flags.append("red_flags_quarantined_unreviewed")
        text = row["user_input"]
        cases.append(
            CanonicalCase(
                case_id=f"carecompass:{row['id']}",
                source=Source.CARECOMPASS,
                scenario_group_id=f"cc:{family}",
                split=Split.UNASSIGNED,
                fold=table.fold_of(family),
                language=LanguageInfo(declared=row["detected_language"], script=detect_script(text)),
                utterances=[Utterance(text_original=text, text_normalized=normalize_text(text))],
                demographics=Demographics(),
                source_labels=SourceLabels(care_type=care, urgency=urg, red_flags_raw=red),
                approved_labels=ApprovedLabels(care_type=approved_care, urgency=approved_urg),
                request_context=RequestContext(lat=float(row["lat"]), lng=float(row["lng"])),
                reference={k: row[k] for k in REFERENCE_FIELDS if row.get(k, "") != ""},
                quality_flags=flags,
                review=Review(clinical_review_status=ReviewStatus.UNREVIEWED,
                              mapping_version=adapter.mapping_version),
                provenance=Provenance(source_row_id=row["id"], source_file=SOURCE_FILE,
                                      generation_method="source"),
            )
        )
    return cases
