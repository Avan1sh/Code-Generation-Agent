import re

from pydantic import BaseModel, model_validator


class Measurement(BaseModel):
    value: float
    unit: str

    @model_validator(mode="before")
    @classmethod
    def expand_raw(cls, data):
        if isinstance(data, dict) and "raw" in data:
            match = re.match(r"^\s*([0-9.]+)\s*([A-Za-z]+)\s*$", str(data["raw"]))
            if match:
                rest = {k: v for k, v in data.items() if k != "raw"}
                rest["value"] = match.group(1)
                rest["unit"] = match.group(2)
                return rest
        return data


def parse_measurement(data: dict) -> Measurement:
    return Measurement.model_validate(data)
