from enum import Enum

from pydantic import BaseModel, ConfigDict


class Colour(str, Enum):
    RED = "red"
    BLUE = "blue"


class Paint(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    colour: Colour
