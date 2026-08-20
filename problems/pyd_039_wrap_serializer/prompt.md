Write a Python module whose model serialises itself INSIDE an
envelope, by wrapping its own normal serialisation rather than rebuilding it.

Requirements:
- A model `Event` with fields `name: str` and `value: int`.
- Serialising an `Event` must produce
  `{"kind": "event", "data": {"name": ..., "value": ...}}`.
- The inner `data` must come from the model's OWN default serialisation, not from
  a hand-built dict -- so adding a field later would flow through automatically.
- JSON serialisation must produce the same envelope.

The module must expose the name `Event`.
