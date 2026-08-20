Write a Python module defining a REUSABLE validated type, attached to
the type annotation itself rather than declared as a decorated method on one
model.

Requirements:
- A type alias `Slug` for a string that is stripped of surrounding whitespace and
  lowercased BEFORE validation, then rejected AFTER validation if the result is
  empty or contains a space, raising a `ValueError` with the message
  `invalid slug`.
- Two models, `Post` and `Tag`, each with a field of that type named `slug`,
  both getting the behaviour without repeating the validation logic.

The module must expose the names `Slug`, `Post`, and `Tag`.
