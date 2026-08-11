from pydantic import BaseModel, field_validator


class Article(BaseModel):
    title: str
    tags: list[str]

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, v):
        if isinstance(v, str):
            return [part.strip() for part in v.split(",") if part.strip()]
        return v
