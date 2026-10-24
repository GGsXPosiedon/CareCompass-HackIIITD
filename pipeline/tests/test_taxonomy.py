import pytest

from ccpipe.taxonomy import (ForbiddenTransformError, TaxonomyError, UnapprovedMappingError,
                             assert_allowed_target, load_label_adapter, load_taxonomy)


@pytest.fixture(scope="module")
def tax():
    return load_taxonomy()


def test_valid_pairs(tax):
    tax.validate_labels("emergency_112", "emergency")
    tax.validate_labels("teleconsultation", "same_day")
    tax.validate_labels(None, None)


def test_invalid_pairs(tax):
    with pytest.raises(TaxonomyError):
        tax.validate_labels("emergency_112", "scheduled")
    with pytest.raises(TaxonomyError):
        tax.validate_labels("home_nursing", "emergency")
    with pytest.raises(TaxonomyError):
        tax.validate_labels("specialist", "scheduled")
    with pytest.raises(TaxonomyError):
        tax.validate_labels("home_nursing", None)


@pytest.mark.parametrize("src,field,target", [
    ("synapse", "severity", "urgency"),
    ("synapse", "recommendation", "care_type"),
    ("ddxplus", "pathology", "urgency"),
    ("ddxplus", "condition_severity", "urgency"),
    ("mediq", "answer", "care_type"),
])
def test_forbidden_transforms(src, field, target):
    with pytest.raises(ForbiddenTransformError):
        assert_allowed_target(src, field, target)


def test_adapter_refuses_problem_statement_vocabulary():
    adapter = load_label_adapter()
    assert adapter.serialize_urgency("same_day") == "same_day"
    with pytest.raises(UnapprovedMappingError):
        adapter.serialize_urgency("emergency", vocabulary="problem_statement")
