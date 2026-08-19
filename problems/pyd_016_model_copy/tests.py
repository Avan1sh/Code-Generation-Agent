from solution import User, rename


def test_returns_new_instance():
    u = User(name="ada", email="a@b.com")
    r = rename(u, "grace")
    assert r is not u


def test_name_replaced():
    r = rename(User(name="ada", email="a@b.com"), "grace")
    assert r.name == "grace"


def test_other_fields_preserved():
    r = rename(User(name="ada", email="a@b.com"), "grace")
    assert r.email == "a@b.com"


def test_original_unmodified():
    u = User(name="ada", email="a@b.com")
    rename(u, "grace")
    assert u.name == "ada"
