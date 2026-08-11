Write a Python module for parsing untrusted input into a Pydantic model.

Requirements:
- A model `Event` with fields `name: str` and `count: int`.
- A function `from_dict(data: dict) -> Event` that validates a dict into an
  `Event`.
- A function `from_json(raw: str) -> Event` that validates a JSON string into
  an `Event` directly, without calling `json.loads` yourself.

Both functions must let Pydantic's `ValidationError` propagate on bad input.

The module must expose the names `Event`, `from_dict`, and `from_json`.
