import pytest
from pydantic import ValidationError

from solution import Order


def test_valid():
    assert Order(quantity=3).quantity == 3


def test_error_type_is_machine_readable():
    with pytest.raises(ValidationError) as exc:
        Order(quantity=0)
    assert exc.value.errors()[0]["type"] == "quantity_not_positive"


def test_error_carries_context():
    with pytest.raises(ValidationError) as exc:
        Order(quantity=-5)
    assert exc.value.errors()[0]["ctx"]["got"] == -5


def test_message_includes_value():
    with pytest.raises(ValidationError) as exc:
        Order(quantity=-5)
    assert "-5" in exc.value.errors()[0]["msg"]
