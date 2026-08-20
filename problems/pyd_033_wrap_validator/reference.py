from pydantic import BaseModel, ValidationError, field_validator


class Server(BaseModel):
    port: int = 8080

    @field_validator("port", mode="wrap")
    @classmethod
    def fallback(cls, value, handler):
        try:
            return handler(value)
        except ValidationError:
            return 8080
