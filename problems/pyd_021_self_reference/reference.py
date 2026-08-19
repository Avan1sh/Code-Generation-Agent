from __future__ import annotations

from pydantic import BaseModel, Field


class Node(BaseModel):
    value: int
    children: list["Node"] = Field(default_factory=list)


Node.model_rebuild()


def parse_tree(data: dict) -> Node:
    return Node.model_validate(data)
