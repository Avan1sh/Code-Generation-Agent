Write a Python module defining a Pydantic model `DateRange`.

Requirements:
- Fields `start: int` and `end: int` (treat them as day numbers).
- A whole-model validation step that runs after the individual fields are
  validated and raises a `ValueError` with the message `end must be after start`
  when `end <= start`.
- A property `length` returning `end - start`.

The module must expose the name `DateRange`.
