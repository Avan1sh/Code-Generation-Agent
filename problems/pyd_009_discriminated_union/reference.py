from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class Circle(BaseModel):
    kind: Literal["circle"]
    radius: float


class Square(BaseModel):
    kind: Literal["square"]
    side: float


Shape = Annotated[Union[Circle, Square], Field(discriminator="kind")]


class Drawing(BaseModel):
    shape: Shape


def parse_drawing(data: dict) -> Drawing:
    return Drawing.model_validate(data)
