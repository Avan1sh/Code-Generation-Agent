from typing import Literal

from pydantic import BaseModel


class Envelope(BaseModel):
    version: Literal["v2"] = "v2"
    payload: dict
