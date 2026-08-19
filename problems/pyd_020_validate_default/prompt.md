Write a Python module defining a Pydantic model `Job`.

Requirements:
- Field `name: str`.
- Field `priority: int` defaulting to `0`.
- A validator on `priority` that rejects negative values with a `ValueError`
  whose message is `priority must not be negative`, AND which also runs against
  the DEFAULT value when `priority` is not supplied at all.
- Demonstrate that the default is validated: a second model `BadJob` identical
  to `Job` but whose `priority` default is `-1` must raise a `ValidationError`
  when constructed without an explicit priority.

The module must expose the names `Job` and `BadJob`.
