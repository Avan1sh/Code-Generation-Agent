from pydantic import AliasChoices, BaseModel, Field


class Telemetry(BaseModel):
    device_id: str = Field(validation_alias=AliasChoices("deviceId", "device_id", "id"))
    temperature: float = Field(validation_alias=AliasChoices("temp", "temperature"))


def parse_telemetry(data: dict) -> Telemetry:
    return Telemetry.model_validate(data)
