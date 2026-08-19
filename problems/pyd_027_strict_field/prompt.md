Write a Python module defining a Pydantic model `Counter` that
refuses type coercion.

Requirements:
- Field `count: int` which must accept ONLY a real integer. Passing the string
  `"5"` must raise a `ValidationError` rather than being coerced to `5`.
- Field `label: str` which behaves normally (no strictness requirement).

The module must expose the name `Counter`.
