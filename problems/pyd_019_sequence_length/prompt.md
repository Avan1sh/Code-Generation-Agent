Write a Python module defining a Pydantic model `Playlist`.

Requirements:
- Field `name: str`.
- Field `tracks: list[str]` constrained to hold at least 1 and at most 3 items.

Use Pydantic's declarative field constraints rather than a hand-written
validator function. Violations must raise a `ValidationError`.

The module must expose the name `Playlist`.
