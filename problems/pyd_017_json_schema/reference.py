from pydantic import BaseModel


class Book(BaseModel):
    title: str
    pages: int


def schema_of() -> dict:
    return Book.model_json_schema()
