import pytest
from pydantic import ValidationError

from solution import DateRange


def test_valid_range():
    r = DateRange(start=1, end=5)
    assert r.start == 1
    assert r.end == 5


def test_length_property():
    assert DateRange(start=2, end=10).length == 8


def test_end_before_start_rejected():
    with pytest.raises(ValidationError) as exc:
        DateRange(start=10, end=2)
    assert "end must be after start" in str(exc.value)


def test_equal_bounds_rejected():
    with pytest.raises(ValidationError) as exc:
        DateRange(start=3, end=3)
    assert "end must be after start" in str(exc.value)


def test_field_types_still_enforced():
    with pytest.raises(ValidationError):
        DateRange(start="not-an-int", end=5)
