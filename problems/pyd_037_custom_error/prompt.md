Write a Python module whose validation failure carries a
MACHINE-READABLE error code and interpolated context, not just a message string.

Requirements:
- A model `Order` with field `quantity: int`.
- A non-positive quantity must fail validation such that the raised error's
  entry has its `type` equal to the exact string `quantity_not_positive`, and a
  message that includes the offending value.
- The error entry must also carry the offending value under a `ctx` key named
  `got`.

The module must expose the name `Order`.
