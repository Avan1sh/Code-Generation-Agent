from pydantic import BaseModel, Field


class Record(BaseModel):
    created_at: str = Field(
        validation_alias="createdAt",
        serialization_alias="created_timestamp",
    )


def dump_record(record: Record) -> dict:
    return record.model_dump(by_alias=True)
