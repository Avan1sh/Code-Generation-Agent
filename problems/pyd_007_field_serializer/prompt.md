Write a Python module defining a Pydantic model `Transaction`.

Requirements:
- Fields `tx_id: str` and `amount_cents: int`.
- When the model is serialised, `amount_cents` must be emitted as a string in
  currency form with two decimal places — for example `1050` serialises to
  `"10.50"`. The in-memory attribute must remain the integer.
- Serialising to JSON must produce the same string form.

The module must expose the name `Transaction`.
