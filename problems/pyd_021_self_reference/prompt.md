Write a Python module defining a self-referencing Pydantic model.

Requirements:
- A model `Node` with fields `value: int` and `children: list[Node]` defaulting
  to an empty list, where `children` holds further `Node` instances.
- A function `parse_tree(data: dict) -> Node` that validates a nested mapping
  into a `Node`.
- Ensure the forward reference to `Node` is resolved so the model is usable.

The module must expose the names `Node` and `parse_tree`.
