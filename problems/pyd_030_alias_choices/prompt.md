Write a Python module defining a Pydantic model `Telemetry` that
accepts SEVERAL possible incoming names for the same field.

Requirements:
- One field stored as `device_id: str`, which must be populated from ANY of the
  incoming keys `deviceId`, `device_id`, or `id`.
- One field stored as `temperature: float`, populated from either `temp` or
  `temperature`.
- A function `parse_telemetry(data: dict) -> Telemetry`.

The module must expose the names `Telemetry` and `parse_telemetry`.
