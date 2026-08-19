Write a Python module defining a Pydantic model `Basket`.

Requirements:
- Field `owner: str`.
- Field `items: list[str]` that defaults to an EMPTY list, where each instance
  gets its own fresh list -- appending to one instance's list must not affect
  another instance.
- Field `meta: dict` that defaults to an empty dict with the same per-instance
  guarantee.

The module must expose the name `Basket`.
