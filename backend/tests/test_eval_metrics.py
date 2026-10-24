import pytest
from eval.run_eval import macro_f1


def test_macro_f1_matches_hand_calculated_balanced_class_average():
    assert macro_f1([('a', 'a'), ('b', 'b')]) == 1
    assert macro_f1([('a', 'a'), ('b', 'a')]) == pytest.approx(1 / 3)
    assert macro_f1([('a', None), ('b', None)]) == 0
