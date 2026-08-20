import pytest
from pydantic import ValidationError

from solution import Page, parse_page


def test_int_page():
    p = parse_page(Page[int], {"items": [1, 2], "total": 2})
    assert p.items == [1, 2]
    assert p.total == 2


def test_str_page():
    p = parse_page(Page[str], {"items": ["a"], "total": 1})
    assert p.items == ["a"]


def test_parameter_is_enforced():
    with pytest.raises(ValidationError):
        parse_page(Page[int], {"items": ["a"], "total": 1})


def test_distinct_parameterisations():
    assert Page[int] is not Page[str]
