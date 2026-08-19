Write a Python module defining a Pydantic model `Signup`.

Requirements:
- Fields `password: str` and `confirm: str`, in that declaration order.
- Validation on `confirm` that compares it against the already-validated
  `password` value and raises a `ValueError` with the message
  `passwords do not match` when they differ.
- The comparison must read the other field from the validation context supplied
  to the validator, not by re-declaring the model.

The module must expose the name `Signup`.
