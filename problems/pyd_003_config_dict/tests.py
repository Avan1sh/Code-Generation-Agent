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
    assert Settings.model_config.get("frozen") is True
    assert Settings.model_config.get("extra") == "forbid"


def test_does_not_use_v1_class_config():
    # Pydantic v2 still HONOURS a v1 `class Config` for backwards compatibility:
    # it populates model_config and every behavioural test above passes either
    # way. So asserting on model_config alone does not distinguish v1 from v2
    # style -- the surviving `Config` attribute is what does.
    assert not hasattr(Settings, "Config"), "use model_config = ConfigDict(...), not class Config"
