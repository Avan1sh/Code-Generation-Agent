Write a Python module where a field declared as a BASE type must
serialise ALL the fields of whatever SUBCLASS instance it actually holds.

Requirements:
- A model `Animal` with field `name: str`.
- A model `Dog` extending `Animal` with an extra field `breed: str`.
- A model `Shelter` with a field `resident` DECLARED as `Animal`.
- Serialising a `Shelter` that holds a `Dog` must emit BOTH `name` and `breed`.
  By default Pydantic v2 emits only the fields of the declared type, so this
  behaviour must be requested explicitly.

The module must expose the names `Animal`, `Dog`, and `Shelter`.
