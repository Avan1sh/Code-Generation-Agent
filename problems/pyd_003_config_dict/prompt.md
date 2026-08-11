Write a Python module defining a Pydantic model `Settings`.

Requirements:
- Fields `host: str` and `port: int`.
- The model must be immutable: assigning to an attribute after construction
  must raise an error.
- The model must reject unknown fields passed to the constructor with a
  validation error (rather than ignoring them).
- Whitespace must be stripped from string values automatically.

The module must expose the name `Settings`.
