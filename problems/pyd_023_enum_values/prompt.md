Write a Python module defining a Pydantic model that stores enum
members by their VALUE rather than as enum instances.

Requirements:
- A `str`-based enum `Colour` with members `RED = "red"` and `BLUE = "blue"`.
- A model `Paint` with field `colour: Colour`.
- After construction, `paint.colour` must be the plain string (e.g. `"red"`),
  NOT the enum member. Configure the model to do this rather than converting by
  hand in a validator.

The module must expose the names `Colour` and `Paint`.
