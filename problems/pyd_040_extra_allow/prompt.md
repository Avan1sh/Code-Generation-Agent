Write a Python module for a model that KEEPS unknown input keys
rather than rejecting or discarding them.

Requirements:
- A model `Flexible` with a declared field `known: str`, configured to accept
  arbitrary additional keys.
- A function `extras_of(model: Flexible) -> dict` returning ONLY the undeclared
  keys that were supplied, excluding `known`.
- The extra values must also survive serialisation.

The module must expose the names `Flexible` and `extras_of`.
