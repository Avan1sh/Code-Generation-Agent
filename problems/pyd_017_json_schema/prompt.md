Write a Python module that exposes a Pydantic model's JSON Schema.

Requirements:
- A model `Book` with fields `title: str` and `pages: int`.
- A function `schema_of() -> dict` returning the JSON Schema for `Book` as a
  plain dict.

The module must expose the names `Book` and `schema_of`.
