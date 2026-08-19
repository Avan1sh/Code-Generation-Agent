from pydantic import BaseModel, ValidationInfo, field_validator


class Signup(BaseModel):
    password: str
    confirm: str

    @field_validator("confirm")
    @classmethod
    def check_match(cls, v: str, info: ValidationInfo) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("passwords do not match")
        return v
