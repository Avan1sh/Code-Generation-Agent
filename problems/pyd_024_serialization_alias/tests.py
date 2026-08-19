from solution import Record, dump_record


def test_populated_from_input_alias():
    r = Record(createdAt="2024-01-01")
    assert r.created_at == "2024-01-01"


def test_serialises_under_output_alias():
    r = Record(createdAt="2024-01-01")
    assert dump_record(r) == {"created_timestamp": "2024-01-01"}


def test_output_key_differs_from_input_key():
    out = dump_record(Record(createdAt="2024-01-01"))
    assert "createdAt" not in out
    assert "created_at" not in out
