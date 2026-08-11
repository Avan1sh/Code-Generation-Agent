from pydantic import BaseModel, field_validator


class Account(BaseModel):
    username: str
    balance: float = 0.0

    @field_validator("username")
    @classmethod
    def normalise_username(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("username must not be blank")
        return cleaned

    @field_validator("balance")
    @classmethod
    def check_balance(cls, v: float) -> float:
        if v < 0:
            raise ValueError("balance must not be negative")
        return v
