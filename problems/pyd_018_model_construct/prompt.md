Write a Python module that builds a model instance while SKIPPING
validation entirely.

Requirements:
- A model `Item` with fields `sku: str` and `qty: int`.
- A function `unsafe_build(data: dict) -> Item` that produces an `Item` from the
  supplied mapping WITHOUT running any validation, so that values of the wrong
  type are stored as given rather than raising.

The module must expose the names `Item` and `unsafe_build`.
