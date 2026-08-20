import json

from solution import Event


def test_envelope_shape():
    assert Event(name="click", value=1).model_dump() == {
        "kind": "event",
        "data": {"name": "click", "value": 1},
    }


def test_json_envelope():
    parsed = json.loads(Event(name="click", value=2).model_dump_json())
    assert parsed["kind"] == "event"
    assert parsed["data"]["value"] == 2


def test_inner_data_is_not_hand_built():
    import inspect

    import solution

    src = inspect.getsource(solution)
    assert "\"name\":" not in src, "inner data must come from default serialisation"
