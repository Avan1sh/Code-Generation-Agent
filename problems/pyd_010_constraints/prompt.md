Write a Python module defining a Pydantic model `Registration`.

Requirements:
- Field `email: str` that must match a basic pattern containing an `@`.
- Field `age: int` constrained to be at least 13 and at most 120.
- Field `tags: list[str]` constrained to have at most 5 items, defaulting to an
  empty list.

Use Pydantic's declarative field constraints (not hand-written validator
functions). Invalid values must raise a `ValidationError`.

The module must expose the name `Registration`.
