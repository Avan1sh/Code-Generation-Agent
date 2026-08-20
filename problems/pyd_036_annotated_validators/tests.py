import pytest
from pydantic import ValidationError

from solution import Post, Slug, Tag


def test_normalises():
    assert Post(slug="  HelloWorld  ").slug == "helloworld"


def test_same_behaviour_on_second_model():
    assert Tag(slug="  ABC ").slug == "abc"


def test_empty_rejected():
    with pytest.raises(ValidationError) as exc:
        Post(slug="   ")
    assert "invalid slug" in str(exc.value)


def test_space_inside_rejected():
    with pytest.raises(ValidationError) as exc:
        Post(slug="hello world")
    assert "invalid slug" in str(exc.value)


def test_logic_is_not_duplicated():
    import inspect

    import solution

    src = inspect.getsource(solution)
    assert src.count("invalid slug") == 1, "the rule must live in the reusable type, not per model"
