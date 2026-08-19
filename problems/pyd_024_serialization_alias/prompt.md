Write a Python module defining a Pydantic model `Record` whose INPUT
key and OUTPUT key for the same field differ.

Requirements:
- One field stored on the instance as `created_at: str`.
- It must be populated from the incoming key `createdAt`.
- When the model is serialised with aliases enabled, that field must be emitted
  under the DIFFERENT key `created_timestamp`.
- A function `dump_record(record: Record) -> dict` returning the alias-based
  serialised form.

The module must expose the names `Record` and `dump_record`.
