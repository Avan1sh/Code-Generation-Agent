from solution import Contact, to_sparse


def test_all_present():
    c = Contact(name="ada", email="a@b.com", phone="123")
    assert to_sparse(c) == {"name": "ada", "email": "a@b.com", "phone": "123"}


def test_none_fields_dropped():
    assert to_sparse(Contact(name="ada")) == {"name": "ada"}


def test_partial():
    assert to_sparse(Contact(name="ada", email="a@b.com")) == {"name": "ada", "email": "a@b.com"}


def test_returns_dict():
    assert isinstance(to_sparse(Contact(name="ada")), dict)
