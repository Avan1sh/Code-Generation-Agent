from pydantic import BaseModel, TypeAdapter


class Point(BaseModel):
    x: int
    y: int


_adapter = TypeAdapter(list[Point])


def parse_points(data: list) -> list[Point]:
    return _adapter.validate_python(data)


def parse_points_json(raw: str) -> list[Point]:
    return _adapter.validate_json(raw)
