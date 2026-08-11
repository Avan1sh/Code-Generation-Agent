Write a Python module defining a Pydantic model `Article`.

Requirements:
- Field `title: str`.
- Field `tags: list[str]`. The input may arrive either as a real list, or as a
  single comma-separated string such as `"python, pydantic, agents"`. When a
  string arrives it must be split on commas and each tag stripped of
  surrounding whitespace **before** the `list[str]` type validation runs.
- Empty segments must be dropped, so `"a,,b"` yields `["a", "b"]`.

The module must expose the name `Article`.
