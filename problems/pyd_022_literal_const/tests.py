import pytest
from pydantic import ValidationError

from solution import Envelope


def test_default_version():
    assert Envelope(payload={}).version == "v2"


def test_explicit_correct_version():
    assert Envelope(version="v2", payload={"a": 1}).version == "v2"


def test_payload_kept():
    assert Envelope(payload={"a": 1}).payload == {"a": 1}


def test_wrong_version_rejected():
    with pytest.raises(ValidationError):
        Envelope(version="v1", payload={})
