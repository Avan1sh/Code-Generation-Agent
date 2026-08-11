Write a Python module defining a Pydantic model `Account`.

Requirements:
- Field `username: str`.
- Field `balance: float`, defaulting to `0.0`.
- Validation on `username`: it must be stripped of surrounding whitespace and
  lowercased before being stored. If the result is empty, raise a `ValueError`
  with the message `username must not be blank`.
- Validation on `balance`: raise a `ValueError` with the message
  `balance must not be negative` if a negative value is supplied.

The module must expose the name `Account`.
