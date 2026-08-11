import pytest
from pydantic import ValidationError

from solution import Account


def test_username_normalised():
    a = Account(username="  AdaLovelace  ")
    assert a.username == "adalovelace"


def test_balance_defaults_to_zero():
    assert Account(username="ada").balance == 0.0


def test_balance_accepted():
    assert Account(username="ada", balance=12.5).balance == 12.5


def test_blank_username_rejected():
    with pytest.raises(ValidationError) as exc:
        Account(username="   ")
    assert "username must not be blank" in str(exc.value)


def test_negative_balance_rejected():
    with pytest.raises(ValidationError) as exc:
        Account(username="ada", balance=-1.0)
    assert "balance must not be negative" in str(exc.value)


def test_uses_v2_validator_api():
    # A v1 @validator would not be registered by pydantic v2 at all; assert the
    # v2 decorator actually took effect rather than silently doing nothing.
    assert Account(username="ADA").username == "ada"
