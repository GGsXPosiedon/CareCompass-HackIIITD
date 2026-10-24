"""Unique-utterance table for triage. Duplicated texts (same text, different lat/lng) collapse to one row."""
from __future__ import annotations

import pandas as pd

from ..families import load_family_table
from ..paths import CONFIG_DIR, data_file

FOLLOWUP = "ask_followup"  # rows with no care_type but a follow_up_question: the dataset's own "ask more" signal
CLASSES = ["emergency_112", "home_nursing", "lab_test_home", "paramedic_home_visit", "teleconsultation", FOLLOWUP]
URGENCY_OF = {"emergency_112": "emergency", "home_nursing": "same_day", "paramedic_home_visit": "same_day",
              "teleconsultation": "same_day", "lab_test_home": "scheduled"}


def load_unique() -> pd.DataFrame:
    df = pd.read_csv(data_file("carecompass_csv"), dtype=str, keep_default_na=False)
    table = load_family_table(CONFIG_DIR / "scenario_families.yaml")
    bad = df[(df["care_type"] == "") & (df["follow_up_question"] == "")]
    if len(bad):
        raise ValueError("rows with neither a label nor a follow-up question")
    df["label"] = df["care_type"].where(df["care_type"] != "", FOLLOWUP)
    g = df.groupby("user_input").agg(label=("label", "first"), n_labels=("label", "nunique"), rows=("id", "count"),
                                     language=("detected_language", "first"), urgency=("urgency", "first")).reset_index()
    if (g["n_labels"] > 1).any():
        raise ValueError("same text carries conflicting labels")
    g["family"] = [table.family_of(t) for t in g["user_input"]]
    g["fold"] = [table.fold_of(f) for f in g["family"]]
    return g.rename(columns={"user_input": "text"}).drop(columns="n_labels").sort_values(["family", "text"]).reset_index(drop=True)
