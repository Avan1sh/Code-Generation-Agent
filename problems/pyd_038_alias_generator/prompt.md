Write a Python module where EVERY field's external name is derived
automatically, without writing an alias on each field.

Requirements:
- A model `ApiPayload` with fields `user_name: str`, `created_at: str`, and
  `is_active: bool`.
- All three must be populated from camelCase keys (`userName`, `createdAt`,
  `isActive`) WITHOUT declaring an alias on any individual field -- the mapping
  must be generated from the field names.
- The model must also still accept the plain Python field names.
- A function `dump_api(payload: ApiPayload) -> dict` emitting the camelCase form.

The module must expose the names `ApiPayload` and `dump_api`.
