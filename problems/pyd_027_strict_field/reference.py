from pydantic import BaseModel, Field


class Counter(BaseModel):
    count: int = Field(strict=True)
    label: str
