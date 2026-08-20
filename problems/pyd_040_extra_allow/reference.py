from pydantic import BaseModel, ConfigDict


class Flexible(BaseModel):
    model_config = ConfigDict(extra="allow")

    known: str


def extras_of(model: Flexible) -> dict:
    return dict(model.__pydantic_extra__ or {})
