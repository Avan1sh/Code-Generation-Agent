import inspect

import pytest
from pydantic import ValidationError

import solution
from solution import Point, parse_points, parse_points_json


def test_parse_points():
    pts = parse_points([{"x": 1, "y": 2}, {"x": 3, "y": 4}])
    assert len(pts) == 2
    assert all(isinstance(p, Point) for p in pts)
    assert pts[0].x == 1


def test_parse_points_json():
    pts = parse_points_json('[{"x": 1, "y": 2}]')
    assert len(pts) == 1
    assert isinstance(pts[0], Point)
    assert pts[0].y == 2


def test_empty_list():
    assert parse_points([]) == []


def test_invalid_item_rejected():
    with pytest.raises(ValidationError):
        parse_points([{"x": "nope", "y": 2}])


def test_uses_type_adapter():
    src = inspect.getsource(solution)
    assert "TypeAdapter" in src, "use pydantic.TypeAdapter for bare-list validation"
