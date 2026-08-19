Write a Python module defining a Pydantic model `Measurement` that
normalises its INPUT MAPPING before any field validation happens.

Requirements:
- Fields `value: float` and `unit: str`.
- The incoming mapping may instead supply a single key `raw` holding a string
  such as `"12.5kg"`. When it does, split it into the numeric part and the unit
  part and validate those as `value` and `unit`.
- This restructuring must happen BEFORE field validation, so that `value` is
  validated as a float in both cases.
- A function `parse_measurement(data: dict) -> Measurement`.

The module must expose the names `Measurement` and `parse_measurement`.
