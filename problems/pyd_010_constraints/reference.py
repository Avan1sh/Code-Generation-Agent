from pydantic import BaseModel, Field


class Registration(BaseModel):
    email: str = Field(pattern=r".+@.+")
    age: int = Field(ge=13, le=120)
    tags: list[str] = Field(default_factory=list, max_length=5)
