Write a Python module defining a REUSABLE, parameterised container model.

Requirements:
- A model `Page` parameterised by an item type, so that `Page[int]` and
  `Page[str]` each validate their contents accordingly.
- Fields `items` (a list of the parameter type) and `total: int`.
- Validating `{"items": ["a"], "total": 1}` as a `Page[int]` must raise a
  `ValidationError`, while the same data as a `Page[str]` must succeed.
- A function `parse_page(model_cls, data: dict)` returning a validated instance.

The module must expose the names `Page` and `parse_page`.
