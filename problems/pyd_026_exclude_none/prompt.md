Write a Python module for serialising a model while dropping empty
values.

Requirements:
- A model `Contact` with fields `name: str`, `email` (string or nothing,
  optional, default nothing), and `phone` (string or nothing, optional, default
  nothing).
- A function `to_sparse(contact: Contact) -> dict` returning the serialised model
  with every field whose value is `None` omitted entirely.

The module must expose the names `Contact` and `to_sparse`.
