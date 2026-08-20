from solution import ApiPayload, dump_api


def test_camel_input():
    p = ApiPayload(userName="ada", createdAt="2024", isActive=True)
    assert p.user_name == "ada"
    assert p.created_at == "2024"
    assert p.is_active is True


def test_python_names_also_accepted():
    p = ApiPayload(user_name="ada", created_at="2024", is_active=False)
    assert p.user_name == "ada"


def test_dump_is_camel():
    p = ApiPayload(userName="ada", createdAt="2024", isActive=True)
    assert dump_api(p) == {"userName": "ada", "createdAt": "2024", "isActive": True}


def test_no_per_field_alias_declared():
    import inspect

    import solution

    src = inspect.getsource(solution)
    # Must not match by_alias=True, which the correct solution legitimately uses;
    # only a literal per-field alias assignment counts as a violation.
    assert 'alias="' not in src, "the mapping must be generated, not written per field"
    assert "alias='" not in src, "the mapping must be generated, not written per field"
