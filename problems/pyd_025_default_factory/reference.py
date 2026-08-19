from pydantic import BaseModel, Field


class Basket(BaseModel):
    owner: str
    items: list[str] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
