Write a Python module defining a Pydantic model `Envelope`.

Requirements:
- Field `version` which must ALWAYS equal the string `"v2"` and may not hold any
  other value; supplying anything else must raise a `ValidationError`.
- Field `payload: dict`.
- Omitting `version` entirely must be accepted and produce `"v2"`.

The module must expose the name `Envelope`.
