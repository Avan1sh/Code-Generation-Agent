import pytest
from pydantic import ValidationError

from solution import Tags, parse_tags


def test_validate_list():
    t = Tags.model_validate(["a", "b"])
    assert t.root == ["a", "b"]


def test_parse_tags_from_json():
    t = parse_tags('["x", "y", "z"]')
    assert t.root == ["x", "y", "z"]


def test_empty_list():
    assert parse_tags("[]").root == []


def test_wrong_item_type_rejected():
    with pytest.raises(ValidationError):
        Tags.model_validate([1, 2])


def test_serialises_back_to_a_bare_list():
    assert Tags.model_validate(["a"]).model_dump() == ["a"]
