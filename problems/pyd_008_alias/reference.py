from pydantic import BaseModel, ConfigDict, Field


class ApiUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(alias="userId")
    display_name: str = Field(alias="displayName")


def dump_api(user: ApiUser) -> dict:
    return user.model_dump(by_alias=True)
