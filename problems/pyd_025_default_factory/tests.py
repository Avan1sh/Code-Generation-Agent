from solution import Basket


def test_defaults_empty():
    b = Basket(owner="ada")
    assert b.items == []
    assert b.meta == {}


def test_lists_not_shared_between_instances():
    a = Basket(owner="a")
    b = Basket(owner="b")
    a.items.append("x")
    assert b.items == []


def test_dicts_not_shared_between_instances():
    a = Basket(owner="a")
    b = Basket(owner="b")
    a.meta["k"] = 1
    assert b.meta == {}


def test_supplied_values_used():
    assert Basket(owner="ada", items=["x"]).items == ["x"]
