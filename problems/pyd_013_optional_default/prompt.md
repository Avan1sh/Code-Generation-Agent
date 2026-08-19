Write a Python module defining a Pydantic model `Profile`.

Requirements:
- Field `name: str`, always required.
- Field `nickname` which may hold a string or nothing, and which is OPTIONAL to
  supply: constructing a `Profile` without it must succeed and leave it as `None`.
- Field `age` which may hold an integer or nothing, also optional in the same way.

The module must expose the name `Profile`.
