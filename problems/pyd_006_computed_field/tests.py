from solution import Rectangle


def test_area_value():
    assert Rectangle(width=3.0, height=4.0).area == 12.0


def test_area_appears_in_serialised_output():
    dumped = Rectangle(width=3.0, height=4.0).model_dump()
    assert dumped == {"width": 3.0, "height": 4.0, "area": 12.0}


def test_area_appears_in_json_output():
    import json

    parsed = json.loads(Rectangle(width=2.0, height=5.0).model_dump_json())
    assert parsed["area"] == 10.0


def test_area_not_a_constructor_field():
    assert "area" not in Rectangle.model_fields
