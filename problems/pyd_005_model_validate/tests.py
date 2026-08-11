import pytest
from pydantic import ValidationError

from solution import Event, from_dict, from_json


def test_from_dict():
    e = from_dict({"name": "click", "count": 3})
    assert isinstance(e, Event)
    assert e.name == "click"
    assert e.count == 3


def test_from_json():
    e = from_json('{"name": "click", "count": 3}')
    assert isinstance(e, Event)
    assert e.count == 3


def test_from_dict_rejects_bad_type():
    with pytest.raises(ValidationError):
        from_dict({"name": "click", "count": "not-a-number"})


def test_from_json_rejects_missing_field():
    with pytest.raises(ValidationError):
        from_json('{"name": "click"}')


def test_from_json_does_not_use_manual_json_loads():
    import inspect

    import solution

    src = inspect.getsource(solution.from_json)
    assert "json.loads" not in src, "use model_validate_json, not json.loads"
