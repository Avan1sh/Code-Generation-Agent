from pydantic import BaseModel


class Patch(BaseModel):
    name: str | None = None
    email: str | None = None


def explicitly_set(patch: Patch) -> set[str]:
    return set(patch.model_fields_set)


def to_patch_body(patch: Patch) -> dict:
    return patch.model_dump(exclude_unset=True)
