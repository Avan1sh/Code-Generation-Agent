import pytest
from pydantic import ValidationError

from solution import Circle, Drawing, Square, parse_drawing


def test_parses_circle():
    d = parse_drawing({"shape": {"kind": "circle", "radius": 2.0}})
    assert isinstance(d.shape, Circle)
    assert d.shape.radius == 2.0


def test_parses_square():
    d = parse_drawing({"shape": {"kind": "square", "side": 3.0}})
    assert isinstance(d.shape, Square)
    assert d.shape.side == 3.0


def test_unknown_kind_rejected():
    with pytest.raises(ValidationError):
        parse_drawing({"shape": {"kind": "triangle", "base": 1.0}})


def test_wrong_payload_for_kind_rejected():
    with pytest.raises(ValidationError):
        parse_drawing({"shape": {"kind": "circle", "side": 3.0}})
