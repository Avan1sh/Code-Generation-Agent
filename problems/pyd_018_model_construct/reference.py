from pydantic import BaseModel


class Item(BaseModel):
    sku: str
    qty: int


def unsafe_build(data: dict) -> Item:
    return Item.model_construct(**data)
