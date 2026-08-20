from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator


def _normalise(value):
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _check(value: str) -> str:
    if not value or " " in value:
        raise ValueError("invalid slug")
    return value


Slug = Annotated[str, BeforeValidator(_normalise), AfterValidator(_check)]


class Post(BaseModel):
    slug: Slug


class Tag(BaseModel):
    slug: Slug
