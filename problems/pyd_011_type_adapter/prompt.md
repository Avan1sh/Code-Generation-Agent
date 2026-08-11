Write a Python module for validating a bare list of models without wrapping it
in a container model.

Requirements:
- A model `Point` with fields `x: int` and `y: int`.
- A function `parse_points(data: list) -> list[Point]` that validates a list of
  dicts into a list of `Point` objects.
- A function `parse_points_json(raw: str) -> list[Point]` that validates a JSON
  array string into a list of `Point` objects.

Use Pydantic's dedicated helper for validating non-model types. Do not define a
wrapper model with a single list field, and do not loop and construct `Point`
one at a time.

The module must expose the names `Point`, `parse_points`, and
`parse_points_json`.
