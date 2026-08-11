from pydantic import BaseModel


class Product(BaseModel):
    sku: str
    name: str
    price: float
    internal_note: str = ""


def to_payload(product: Product) -> dict:
    return product.model_dump(exclude={"internal_note"})


def to_json_payload(product: Product) -> str:
    return product.model_dump_json(exclude={"internal_note"})
