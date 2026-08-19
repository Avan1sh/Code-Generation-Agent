from solution import Item, unsafe_build


def test_builds_valid_data():
    i = unsafe_build({"sku": "A1", "qty": 3})
    assert i.sku == "A1"
    assert i.qty == 3


def test_returns_an_item():
    assert isinstance(unsafe_build({"sku": "A1", "qty": 1}), Item)


def test_skips_validation():
    i = unsafe_build({"sku": "A1", "qty": "not-a-number"})
    assert i.qty == "not-a-number"


def test_normal_construction_still_validates():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Item(sku="A1", qty="not-a-number")
