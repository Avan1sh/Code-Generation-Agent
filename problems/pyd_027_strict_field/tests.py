import pytest
from pydantic import ValidationError

from solution import Counter


def test_accepts_real_int():
    assert Counter(count=5, label="x").count == 5


def test_rejects_numeric_string():
    with pytest.raises(ValidationError):
        Counter(count="5", label="x")


def test_rejects_float():
    with pytest.raises(ValidationError):
        Counter(count=5.0, label="x")


def test_label_normal():
    assert Counter(count=1, label="hello").label == "hello"
