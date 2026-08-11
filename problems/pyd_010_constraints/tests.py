import pytest
from pydantic import ValidationError

from solution import Registration


def test_valid():
    r = Registration(email="a@b.com", age=30, tags=["x"])
    assert r.age == 30
    assert r.tags == ["x"]


def test_tags_default_empty():
    assert Registration(email="a@b.com", age=30).tags == []


def test_age_below_minimum_rejected():
    with pytest.raises(ValidationError):
        Registration(email="a@b.com", age=12)


def test_age_above_maximum_rejected():
    with pytest.raises(ValidationError):
        Registration(email="a@b.com", age=121)


def test_boundary_ages_accepted():
    assert Registration(email="a@b.com", age=13).age == 13
    assert Registration(email="a@b.com", age=120).age == 120


def test_bad_email_rejected():
    with pytest.raises(ValidationError):
        Registration(email="not-an-email", age=30)


def test_too_many_tags_rejected():
    with pytest.raises(ValidationError):
        Registration(email="a@b.com", age=30, tags=["a", "b", "c", "d", "e", "f"])
