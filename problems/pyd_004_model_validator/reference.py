from pydantic import BaseModel, model_validator


class DateRange(BaseModel):
    start: int
    end: int

    @model_validator(mode="after")
    def check_order(self) -> "DateRange":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self

    @property
    def length(self) -> int:
        return self.end - self.start
