import pytest
from pydantic import ValidationError

from ccpipe import schemas as s



def test_caregiver_window_validation():
    fields = s.Caregiver.model_fields
    assert "free_from" in fields and "free_until" in fields


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        s.Duration(bucket="x", surprise=1)
