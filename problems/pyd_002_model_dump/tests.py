import json

from solution import Product, to_json_payload, to_payload


def _product():
    return Product(sku="A1", name="Widget", price=9.99, internal_note="secret")


def test_to_payload_is_a_dict():
    payload = to_payload(_product())
    assert isinstance(payload, dict)


def test_to_payload_excludes_internal_note():
    payload = to_payload(_product())
    assert "internal_note" not in payload


def test_to_payload_keeps_other_fields():
    payload = to_payload(_product())
    assert payload == {"sku": "A1", "name": "Widget", "price": 9.99}


def test_to_json_payload_is_a_string():
    assert isinstance(to_json_payload(_product()), str)


def test_to_json_payload_roundtrips_without_internal_note():
    parsed = json.loads(to_json_payload(_product()))
    assert parsed == {"sku": "A1", "name": "Widget", "price": 9.99}


def test_default_internal_note():
    assert Product(sku="A1", name="Widget", price=1.0).internal_note == ""
