Write a Python module for updating a nested Pydantic model.

Requirements:
- A model `Address` with fields `city: str` and `zip_code: str`.
- A model `Person` with fields `name: str` and `address: Address`.
- A function `move(person: Person, new_city: str) -> Person` returning a NEW
  `Person` whose address has the new city, leaving both the original `Person`
  and the original `Address` unmodified.

The module must expose the names `Address`, `Person`, and `move`.
