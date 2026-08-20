from solution import Patch, explicitly_set, to_patch_body


def test_nothing_supplied():
    assert explicitly_set(Patch()) == set()


def test_one_supplied():
    assert explicitly_set(Patch(name="ada")) == {"name"}


def test_explicit_none_counts_as_supplied():
    assert explicitly_set(Patch(email=None)) == {"email"}


def test_patch_body_omits_defaults():
    assert to_patch_body(Patch(name="ada")) == {"name": "ada"}


def test_patch_body_keeps_explicit_none():
    assert to_patch_body(Patch(email=None)) == {"email": None}


def test_patch_body_empty_when_nothing_set():
    assert to_patch_body(Patch()) == {}
