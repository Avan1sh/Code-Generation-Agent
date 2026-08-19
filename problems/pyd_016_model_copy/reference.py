from pydantic import BaseModel


class User(BaseModel):
    name: str
    email: str


def rename(user: User, new_name: str) -> User:
    return user.model_copy(update={"name": new_name})
