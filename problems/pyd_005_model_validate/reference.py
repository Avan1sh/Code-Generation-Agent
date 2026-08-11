from pydantic import BaseModel


class Event(BaseModel):
    name: str
    count: int


def from_dict(data: dict) -> Event:
    return Event.model_validate(data)


def from_json(raw: str) -> Event:
    return Event.model_validate_json(raw)
