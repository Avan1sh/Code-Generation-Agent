import pytest
from pydantic import ValidationError

from solution import Signup


def test_matching_passwords():
    s = Signup(password="hunter2", confirm="hunter2")
    assert s.password == "hunter2"
    assert s.confirm == "hunter2"


def test_mismatch_rejected():
    with pytest.raises(ValidationError) as exc:
        Signup(password="hunter2", confirm="hunter3")
    assert "passwords do not match" in str(exc.value)


def test_empty_strings_match():
    assert Signup(password="", confirm="").confirm == ""


def test_missing_field_rejected():
    with pytest.raises(ValidationError):
        Signup(password="x")
