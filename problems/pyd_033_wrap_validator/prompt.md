Write a Python module defining a model that FALLS BACK to a default
when a field fails its own type validation, instead of raising.

Requirements:
- A model `Server` with field `port: int` defaulting to `8080`.
- If the supplied `port` cannot be validated as an integer, the model must
  silently use `8080` rather than raising a `ValidationError`.
- A valid integer (or a value coercible to one) must be used as given.
- Do this by intercepting the field's own validation step and handling its
  failure, not by pre-checking the type yourself with `isinstance`.

The module must expose the name `Server`.
