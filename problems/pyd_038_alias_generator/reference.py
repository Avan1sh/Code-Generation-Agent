from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiPayload(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    user_name: str
    created_at: str
    is_active: bool


def dump_api(payload: ApiPayload) -> dict:
    return payload.model_dump(by_alias=True)
