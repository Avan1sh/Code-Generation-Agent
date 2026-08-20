from pydantic import BaseModel, model_serializer


class Event(BaseModel):
    name: str
    value: int

    @model_serializer(mode="wrap")
    def envelope(self, handler):
        return {"kind": "event", "data": handler(self)}
