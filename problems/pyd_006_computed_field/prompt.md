Write a Python module defining a Pydantic model `Rectangle`.

Requirements:
- Fields `width: float` and `height: float`.
- An `area` value equal to `width * height` that is computed from the fields and
  is **included in the model's serialised output** (so serialising the model
  produces a dict containing `width`, `height`, and `area`).
- `area` must not be settable via the constructor.

The module must expose the name `Rectangle`.
