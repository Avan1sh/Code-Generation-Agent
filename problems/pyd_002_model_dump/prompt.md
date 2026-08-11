Write a Python module for serialising a Pydantic model.

Requirements:
- A model `Product` with fields `sku: str`, `name: str`, `price: float`, and
  `internal_note: str` defaulting to `""`.
- A function `to_payload(product: Product) -> dict` returning the model as a
  plain dict with `internal_note` excluded.
- A function `to_json_payload(product: Product) -> str` returning the model as a
  JSON string, also excluding `internal_note`.

The module must expose the names `Product`, `to_payload`, and `to_json_payload`.
