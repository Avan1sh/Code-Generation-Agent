Write a Python module modelling two shapes with a discriminated union.

Requirements:
- A model `Circle` with a literal field `kind` fixed to `"circle"` and a field
  `radius: float`.
- A model `Square` with a literal field `kind` fixed to `"square"` and a field
  `side: float`.
- A model `Drawing` with a field `shape` that is a union of `Circle` and
  `Square`, discriminated on the `kind` field.
- A function `parse_drawing(data: dict) -> Drawing`.

Supplying an unknown `kind` must raise a Pydantic `ValidationError`.

The module must expose the names `Circle`, `Square`, `Drawing`, and
`parse_drawing`.
