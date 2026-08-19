Write a Python module defining a Pydantic model `Tags` whose entire
content is a list of strings, rather than an object with a named field.

Requirements:
- Validating the JSON array `["a", "b"]` must produce a `Tags` instance.
- The wrapped list must be reachable on the instance as the attribute `root`.
- A function `parse_tags(raw: str) -> Tags` that validates a JSON array string.

The module must expose the names `Tags` and `parse_tags`.
