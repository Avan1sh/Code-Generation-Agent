from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


def parse_page(model_cls, data: dict):
    return model_cls.model_validate(data)
