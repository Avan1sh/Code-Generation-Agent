import pytest
from pydantic import ValidationError

from solution import Telemetry, parse_telemetry


def test_camel_case_key():
    t = parse_telemetry({"deviceId": "d1", "temp": 20.5})
    assert t.device_id == "d1"
    assert t.temperature == 20.5


def test_snake_case_key():
    t = parse_telemetry({"device_id": "d2", "temperature": 21.0})
    assert t.device_id == "d2"
    assert t.temperature == 21.0


def test_short_key():
    t = parse_telemetry({"id": "d3", "temp": 19.0})
    assert t.device_id == "d3"


def test_missing_rejected():
    with pytest.raises(ValidationError):
        parse_telemetry({"temp": 20.0})
