Write a Python module for duplicating a Pydantic model instance.

Requirements:
- A model `User` with fields `name: str` and `email: str`.
- A function `rename(user: User, new_name: str) -> User` that returns a NEW
  `User` with `name` replaced, leaving the original instance unmodified.
- Do not construct the new instance by hand-passing every field; use the
  model's own duplication facility with an update mapping.

The module must expose the names `User` and `rename`.
