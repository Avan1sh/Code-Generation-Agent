from solution import Address, Person, move


def _person():
    return Person(name="ada", address=Address(city="london", zip_code="E1"))


def test_city_updated():
    assert move(_person(), "paris").address.city == "paris"


def test_zip_preserved():
    assert move(_person(), "paris").address.zip_code == "E1"


def test_name_preserved():
    assert move(_person(), "paris").name == "ada"


def test_original_unmodified():
    p = _person()
    move(p, "paris")
    assert p.address.city == "london"


def test_returns_new_objects():
    p = _person()
    r = move(p, "paris")
    assert r is not p
    assert r.address is not p.address
