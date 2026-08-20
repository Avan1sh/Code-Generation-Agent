from pydantic import BaseModel, SerializeAsAny


class Animal(BaseModel):
    name: str


class Dog(Animal):
    breed: str


class Shelter(BaseModel):
    resident: SerializeAsAny[Animal]
