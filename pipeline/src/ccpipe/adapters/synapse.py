"""SYNAPSE -> CanonicalCase. Severity / recommendation stay source-only, never routing labels."""
from __future__ import annotations

import pandas as pd

from ..schemas import (Assertion, CanonicalCase, Demographics, Duration, Fact, LanguageInfo, Origin,
                       Provenance, ReviewStatus, Review, Source, SourceLabels, Split, Utterance)
from ..splits import normalize_symptoms, symptom_group_id
from ..textutil import normalize_text

SOURCE_FILE = "SYNAPSE_An Expert Annotated Dataset of Patient symptoms and Demographics.csv"


def build_cases(df: pd.DataFrame, group_split: dict[str, str], limit: int | None = None) -> list[CanonicalCase]:
    cases = []
    for i, r in enumerate(df.to_dict("records")):
        if limit is not None and i >= limit:
            break
        group = symptom_group_id(normalize_symptoms(r["Symptoms"]))
        cases.append(CanonicalCase(
            case_id=f"synapse:{i}", source=Source.SYNAPSE,
            scenario_group_id=f"syn:{group}",
            split=Split(group_split[group]),
            language=LanguageInfo(declared="English", script="latin"),
            utterances=[Utterance(text_original=r["Symptoms"], text_normalized=normalize_text(r["Symptoms"]))],
            demographics=Demographics(age_bucket=r["Age"] or None, sex_reported=r["Gender"] or None),
            duration=Duration(bucket=r["Duration"] or None),
            source_labels=SourceLabels(severity=r["Severity"] or None,
                                       recommendation=r["Final Recommendation"] or None),
            review=Review(clinical_review_status=ReviewStatus.UNREVIEWED),
            provenance=Provenance(source_row_id=str(i), source_file=SOURCE_FILE),
        ))
    return cases
