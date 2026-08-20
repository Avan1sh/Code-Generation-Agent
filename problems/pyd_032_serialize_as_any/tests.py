from solution import Animal, Dog, Shelter


def test_base_instance():
    s = Shelter(resident=Animal(name="generic"))
    assert s.model_dump() == {"resident": {"name": "generic"}}


def test_subclass_fields_are_emitted():
    s = Shelter(resident=Dog(name="rex", breed="collie"))
    dumped = s.model_dump()
    assert dumped["resident"]["name"] == "rex"
    assert dumped["resident"]["breed"] == "collie"


def test_json_round_trip_keeps_subclass_fields():
    import json

    s = Shelter(resident=Dog(name="rex", breed="collie"))
    assert json.loads(s.model_dump_json())["resident"]["breed"] == "collie"


def test_dog_is_an_animal():
    assert issubclass(Dog, Animal)
