from pydantic import BaseModel


class Address(BaseModel):
    city: str
    zip_code: str


class Person(BaseModel):
    name: str
    address: Address


def move(person: Person, new_city: str) -> Person:
    new_address = person.address.model_copy(update={"city": new_city})
    return person.model_copy(update={"address": new_address})
