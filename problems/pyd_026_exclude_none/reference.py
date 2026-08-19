from pydantic import BaseModel


class Contact(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None


def to_sparse(contact: Contact) -> dict:
    return contact.model_dump(exclude_none=True)
