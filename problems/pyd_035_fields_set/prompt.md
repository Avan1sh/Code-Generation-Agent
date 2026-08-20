Write a Python module that can distinguish a field EXPLICITLY set to
nothing from one that simply defaulted.

Requirements:
- A model `Patch` with fields `name` and `email`, each holding a string or
  nothing, both defaulting to nothing.
- A function `explicitly_set(patch: Patch) -> set[str]` returning the names of
  the fields that were actually supplied by the caller -- including fields that
  were supplied as an explicit empty value.
- A function `to_patch_body(patch: Patch) -> dict` returning ONLY the explicitly
  supplied fields, so that a field left out is omitted while a field explicitly
  set to nothing is present.

The module must expose the names `Patch`, `explicitly_set`, and `to_patch_body`.
