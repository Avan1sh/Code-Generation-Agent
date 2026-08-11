Write a Python module defining a Pydantic model `ApiUser`.

Requirements:
- Field `user_id: int`, which must accept the incoming key `userId`.
- Field `display_name: str`, which must accept the incoming key `displayName`.
- The model must ALSO accept the plain Python field names (`user_id`,
  `display_name`) when constructed directly.
- A function `dump_api(user: ApiUser) -> dict` that serialises the model back
  out using the camelCase names.

The module must expose the names `ApiUser` and `dump_api`.
