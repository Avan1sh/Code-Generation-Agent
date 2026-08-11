from solution import ApiUser, dump_api


def test_accepts_camel_case_input():
    u = ApiUser(userId=7, displayName="Ada")
    assert u.user_id == 7
    assert u.display_name == "Ada"


def test_accepts_python_field_names():
    u = ApiUser(user_id=7, display_name="Ada")
    assert u.user_id == 7
    assert u.display_name == "Ada"


def test_dump_uses_camel_case():
    u = ApiUser(userId=7, displayName="Ada")
    assert dump_api(u) == {"userId": 7, "displayName": "Ada"}


def test_populate_by_name_enabled():
    # Without this v2 config key, construction by python field name fails.
    assert ApiUser.model_config.get("populate_by_name") is True
