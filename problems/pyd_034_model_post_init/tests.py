from solution import Document


def test_counts_words():
    assert Document(text="one two three").word_count == 3


def test_empty_text():
    assert Document(text="").word_count == 0


def test_not_a_field():
    assert "word_count" not in Document.model_fields


def test_absent_from_serialised_output():
    assert Document(text="a b").model_dump() == {"text": "a b"}


def test_recomputed_per_instance():
    assert Document(text="a").word_count == 1
    assert Document(text="a b c d").word_count == 4
