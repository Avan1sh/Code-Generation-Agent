from pydantic import BaseModel, field_serializer


class Transaction(BaseModel):
    tx_id: str
    amount_cents: int

    @field_serializer("amount_cents")
    def serialize_amount(self, value: int) -> str:
        return f"{value / 100:.2f}"
