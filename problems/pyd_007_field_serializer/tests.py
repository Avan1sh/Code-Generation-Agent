import json

from solution import Transaction


def test_attribute_stays_an_int():
    t = Transaction(tx_id="t1", amount_cents=1050)
    assert t.amount_cents == 1050
    assert isinstance(t.amount_cents, int)


def test_model_dump_formats_currency():
    dumped = Transaction(tx_id="t1", amount_cents=1050).model_dump()
    assert dumped["amount_cents"] == "10.50"


def test_json_dump_formats_currency():
    parsed = json.loads(Transaction(tx_id="t1", amount_cents=1050).model_dump_json())
    assert parsed["amount_cents"] == "10.50"


def test_pads_two_decimal_places():
    assert Transaction(tx_id="t2", amount_cents=5).model_dump()["amount_cents"] == "0.05"


def test_whole_units():
    assert Transaction(tx_id="t3", amount_cents=200).model_dump()["amount_cents"] == "2.00"
