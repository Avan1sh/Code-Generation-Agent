import pytest
from pydantic import ValidationError

from solution import Node, parse_tree


def test_leaf():
    n = parse_tree({"value": 1})
    assert n.value == 1
    assert n.children == []


def test_nested():
    n = parse_tree({"value": 1, "children": [{"value": 2}, {"value": 3}]})
    assert len(n.children) == 2
    assert all(isinstance(c, Node) for c in n.children)
    assert n.children[0].value == 2


def test_deeply_nested():
    n = parse_tree({"value": 1, "children": [{"value": 2, "children": [{"value": 3}]}]})
    assert n.children[0].children[0].value == 3


def test_invalid_child_rejected():
    with pytest.raises(ValidationError):
        parse_tree({"value": 1, "children": [{"value": "nope"}]})
