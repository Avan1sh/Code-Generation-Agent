import pytest
from pydantic import ValidationError

from solution import Colour, Paint


def test_stores_plain_value():
    p = Paint(colour="red")
    assert p.colour == "red"
    assert not isinstance(p.colour, Colour)


def test_accepts_enum_member():
    assert Paint(colour=Colour.BLUE).colour == "blue"


def test_invalid_rejected():
    with pytest.raises(ValidationError):
        Paint(colour="green")


def test_config_flag_set():
    assert Paint.model_config.get("use_enum_values") is True
