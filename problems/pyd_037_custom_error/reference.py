from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError


class Order(BaseModel):
    quantity: int

    @field_validator("quantity")
    @classmethod
    def check_positive(cls, v: int) -> int:
        if v <= 0:
            raise PydanticCustomError(
                "quantity_not_positive",
                "quantity must be positive, got {got}",
                {"got": v},
            )
        return v
