import pytest
from pydantic import ValidationError

from solution import BadJob, Job


def test_default_applies():
    assert Job(name="j").priority == 0


def test_explicit_value():
    assert Job(name="j", priority=5).priority == 5


def test_negative_rejected():
    with pytest.raises(ValidationError) as exc:
        Job(name="j", priority=-2)
    assert "priority must not be negative" in str(exc.value)


def test_bad_default_is_validated():
    # By default Pydantic does NOT validate defaults; this only raises when the
    # field opts in to default validation.
    with pytest.raises(ValidationError):
        BadJob(name="j")
