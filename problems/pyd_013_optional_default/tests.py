import pytest
from pydantic import ValidationError

from solution import Profile


def test_only_name_required():
    p = Profile(name="ada")
    assert p.name == "ada"
    assert p.nickname is None
    assert p.age is None


def test_values_accepted():
    p = Profile(name="ada", nickname="countess", age=36)
    assert p.nickname == "countess"
    assert p.age == 36


def test_explicit_none_accepted():
    assert Profile(name="ada", nickname=None).nickname is None


def test_name_still_required():
    with pytest.raises(ValidationError):
        Profile()


def test_optional_fields_are_not_required():
    # In v1 a bare Optional[X] annotation implied a None default. In v2 it does
    # not -- the default must be written explicitly or the field stays required.
    assert Profile.model_fields["nickname"].is_required() is False
    assert Profile.model_fields["age"].is_required() is False
