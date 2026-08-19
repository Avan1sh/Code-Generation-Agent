from pydantic import BaseModel


class Profile(BaseModel):
    name: str
    nickname: str | None = None
    age: int | None = None
