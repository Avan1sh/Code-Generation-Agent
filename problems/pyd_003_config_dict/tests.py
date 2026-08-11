import pytest
from pydantic import ValidationError

from solution import Settings


def test_constructs():
    s = Settings(host="localhost", port=8080)
    assert s.host == "localhost"
    assert s.port == 8080


def test_is_immutable():
    s = Settings(host="localhost", port=8080)
    with pytest.raises(ValidationError):
        s.port = 9090


def test_rejects_extra_fields():
    with pytest.raises(ValidationError):
        Settings(host="localhost", port=8080, debug=True)


def test_strips_whitespace():
    assert Settings(host="  localhost  ", port=8080).host == "localhost"


def test_config_is_v2_style():
    # model_config is a dict on v2 models; a v1 `class Config` would leave
    # model_config empty and none of the behaviour above would apply.
    assert Settings.model_config.get("frozen") is True
    assert Settings.model_config.get("extra") == "forbid"
