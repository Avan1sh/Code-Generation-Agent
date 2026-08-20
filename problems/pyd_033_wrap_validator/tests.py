from solution import Server


def test_default():
    assert Server().port == 8080


def test_valid_int():
    assert Server(port=9090).port == 9090


def test_coercible_string():
    assert Server(port="9090").port == 9090


def test_garbage_falls_back():
    assert Server(port="not-a-port").port == 8080


def test_none_falls_back():
    assert Server(port=None).port == 8080


def test_does_not_use_isinstance_precheck():
    import inspect

    import solution

    assert "isinstance" not in inspect.getsource(solution), "intercept the validation step instead"
