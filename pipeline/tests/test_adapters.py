import pandas as pd
import pytest

from ccpipe.adapters import caregivers, carecompass, ddxplus
from ccpipe.families import load_family_table
from ccpipe.paths import CONFIG_DIR, data_file
from ccpipe.schemas import Assertion
from ccpipe.taxonomy import load_label_adapter

EVID = {
    "E_1": {"data_type": "B", "value_meaning": {}},
    "E_2": {"data_type": "M", "value_meaning": {"V_1": {"en": "left"}, "V_2": {"en": "right"}}},
    "E_3": {"data_type": "C", "value_meaning": {}},
    "E_4": {"data_type": "C", "value_meaning": {"V_10": {"en": "N"}, "V_12": {"en": "Y"}, "V_5": {"en": "pink"}}},
}


def test_ddx_decode_never_creates_absent():
    st = ddxplus.DecodeStats()
    facts = ddxplus.decode_evidence(
        ["E_1", "E_2_@_V_1", "E_2_@_V_2", "E_3_@_6", "E_4_@_V_10", "E_4_@_V_5", "E_9", "E_2_@_V_99"],
        EVID, "E_1", st)
    by = {f.concept_id: f for f in facts}
    assert by["ddxplus:E_2"].value == ["left", "right"]
    assert by["ddxplus:E_3"].value == 6
    assert by["ddxplus:E_4"].value == "pink"
    assert by["ddxplus:E_1"].is_initial
    assert all(f.assertion is Assertion.PRESENT for f in facts)
    assert st.explicit_no_not_modelled == 1
    assert st.unresolved["E_9"] == 1 and st.unresolved["E_2_@_V_99"] == 1


def test_carecompass_adapter_real_data(cc_csv):
    df = pd.read_csv(cc_csv, dtype=str, keep_default_na=False)
    cases = carecompass.build_cases(df, load_family_table(CONFIG_DIR / "scenario_families.yaml"),
                                    load_label_adapter())
    assert len(cases) == len(df) == 340
    assert all(c.review.mapping_version != "pending" for c in cases)
    assert all(not c.approved_labels.red_flag_ids for c in cases)
    unlabeled = [c for c in cases if c.approved_labels.care_type is None]
    assert len(unlabeled) == 39
    assert len({c.case_id for c in cases}) == 340


def test_caregivers_real_data():
    path = data_file("caregivers")
    if not path.exists():
        pytest.skip("caregivers.csv not available")
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    assert len(caregivers.build_caregivers(df)) == len(df) == 60
