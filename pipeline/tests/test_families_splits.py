import pandas as pd
import pytest

from ccpipe.families import FamilyTable, FamilyTableError, Family, load_family_table, validate_table
from ccpipe.paths import CONFIG_DIR
from ccpipe.splits import (assign_carecompass_folds, assign_group_split, build_synapse_split_table,
                           check_carecompass_leakage, normalize_symptoms, parse_tokens, patient_signature)


@pytest.fixture(scope="module")
def table():
    return load_family_table(CONFIG_DIR / "scenario_families.yaml")


def test_table_shape(table):
    assert len(table.families) == 20
    assert sum(len(f.members) for f in table.families.values()) == 66
    assert set(table.folds) == {"A", "B", "C"}


def test_table_rejects_duplicate_member():
    fams = {"X": Family("X", None, ("a",)), "Y": Family("Y", None, ("a",))}
    with pytest.raises(FamilyTableError):
        FamilyTable(1, fams, {"A": ("X", "Y")})


def test_table_rejects_family_in_two_folds():
    fams = {"X": Family("X", None, ("a",))}
    with pytest.raises(FamilyTableError):
        FamilyTable(1, fams, {"A": ("X",), "B": ("X",)})


def test_real_csv_leakage_free(cc_csv, table):
    df = pd.read_csv(cc_csv, dtype=str, keep_default_na=False)
    validate_table(table, df["user_input"].unique())
    out = assign_carecompass_folds(df, table)
    assert check_carecompass_leakage(out) == []


def test_leakage_detector_fires():
    df = pd.DataFrame({"id": ["1", "2"], "user_input": ["a", "a"], "family_id": ["F", "F"],
                       "fold": ["A", "B"], "care_type": ["x", "x"]})
    assert check_carecompass_leakage(df)


def test_validate_flags_missing(table):
    with pytest.raises(FamilyTableError):
        validate_table(table, ["not a known utterance"])


def test_synapse_split_deterministic_and_grouped():
    s = pd.Series(["Fever  and cough", "fever and cough", "Headache"])
    t = build_synapse_split_table(s)
    assert len(t) == 2  # case/whitespace variants collapse to one group
    assert normalize_symptoms("Fever  and cough") == "fever and cough"
    assert assign_group_split("abc") == assign_group_split("abc")
    assert set(t["split"]) <= {"train", "val", "test"}


def test_ddx_signature_order_invariant():
    assert parse_tokens("['E_1', 'E_2_@_V_3']") == ["E_1", "E_2_@_V_3"]
    a = patient_signature("30", "F", "Flu", ["E_2", "E_1"])
    b = patient_signature("30", "F", "Flu", ["E_1", "E_2"])
    c = patient_signature("31", "F", "Flu", ["E_1", "E_2"])
    assert a == b != c
