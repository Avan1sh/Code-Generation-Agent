from solution import Flexible, extras_of


def test_known_field():
    assert Flexible(known="a").known == "a"


def test_no_extras():
    assert extras_of(Flexible(known="a")) == {}


def test_extras_captured():
    m = Flexible(known="a", other=1, another="x")
    assert extras_of(m) == {"other": 1, "another": "x"}


def test_known_excluded_from_extras():
    assert "known" not in extras_of(Flexible(known="a", other=1))


def test_extras_survive_serialisation():
    dumped = Flexible(known="a", other=1).model_dump()
    assert dumped["known"] == "a"
    assert dumped["other"] == 1
