Write a Python module defining a model that computes a derived value
ONCE after validation completes, and stores it in a NON-field attribute.

Requirements:
- A model `Document` with field `text: str`.
- After validation, the model must compute the number of whitespace-separated
  words in `text` and store it privately.
- The count must be readable as `doc.word_count`.
- `word_count` must NOT be a model field, and must NOT appear in the serialised
  output.

The module must expose the name `Document`.
