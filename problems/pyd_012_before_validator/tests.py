import pytest
from pydantic import ValidationError

from solution import Article


def test_accepts_real_list():
    a = Article(title="t", tags=["python", "pydantic"])
    assert a.tags == ["python", "pydantic"]


def test_splits_comma_separated_string():
    a = Article(title="t", tags="python, pydantic, agents")
    assert a.tags == ["python", "pydantic", "agents"]


def test_strips_whitespace():
    a = Article(title="t", tags="  a  ,  b  ")
    assert a.tags == ["a", "b"]


def test_drops_empty_segments():
    a = Article(title="t", tags="a,,b")
    assert a.tags == ["a", "b"]


def test_single_tag_string():
    assert Article(title="t", tags="solo").tags == ["solo"]


def test_still_rejects_invalid_type():
    with pytest.raises(ValidationError):
        Article(title="t", tags=123)
