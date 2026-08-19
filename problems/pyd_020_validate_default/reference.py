from pydantic import BaseModel, Field, field_validator


class Job(BaseModel):
    name: str
    priority: int = Field(default=0, validate_default=True)

    @field_validator("priority")
    @classmethod
    def check_priority(cls, v: int) -> int:
        if v < 0:
            raise ValueError("priority must not be negative")
        return v


class BadJob(BaseModel):
    name: str
    priority: int = Field(default=-1, validate_default=True)

    @field_validator("priority")
    @classmethod
    def check_priority(cls, v: int) -> int:
        if v < 0:
            raise ValueError("priority must not be negative")
        return v
