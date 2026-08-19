import pytest
from pydantic import ValidationError

from solution import Measurement, parse_measurement


def test_normal_fields():
    m = parse_measurement({"value": 3.0, "unit": "kg"})
    assert m.value == 3.0
    assert m.unit == "kg"


def test_raw_string_split():
    m = parse_measurement({"raw": "12.5kg"})
    assert m.value == 12.5
    assert m.unit == "kg"


def test_raw_integer_like():
    m = parse_measurement({"raw": "7m"})
    assert m.value == 7.0
    assert m.unit == "m"


def test_value_is_a_float():
    assert isinstance(parse_measurement({"raw": "12.5kg"}).value, float)


def test_missing_fields_rejected():
    with pytest.raises(ValidationError):
        parse_measurement({"unit": "kg"})
