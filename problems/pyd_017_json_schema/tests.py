from solution import Book, schema_of


def test_returns_dict():
    assert isinstance(schema_of(), dict)


def test_has_properties():
    s = schema_of()
    assert "properties" in s
    assert set(s["properties"]) == {"title", "pages"}


def test_types_described():
    props = schema_of()["properties"]
    assert props["title"]["type"] == "string"
    assert props["pages"]["type"] == "integer"


def test_required_fields_listed():
    assert set(schema_of()["required"]) == {"title", "pages"}
