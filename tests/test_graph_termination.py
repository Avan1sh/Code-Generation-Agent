"""Proves the retry loop terminates without depending on the model behaving well.

This is the test that backs the "no unbounded loops" claim. It swaps in a stub
LLM that ALWAYS emits Pydantic v1 code -- i.e. the worst case, a model that
never corrects itself no matter how good the reflection is. If the bound were
enforced by anything model-dependent, this test would hang or overrun.

No API key required.
"""

from __future__ import annotations

import pytest

from agent import graph as graph_module
from agent.nodes import generator as generator_module
from agent.nodes import reflector as reflector_module
from agent.nodes import test_generator as test_generator_module
from agent.state import Problem

ALWAYS_V1_CODE = """```python
from pydantic import BaseModel, validator


class User(BaseModel):
    name: str

    @validator("name")
    def check(cls, v):
        return v
```"""

ALWAYS_BROKEN_BUT_V2_CODE = """```python
from pydantic import BaseModel


class User(BaseModel):
    name: str


def add(a, b):
    return a - b
```"""


class _StubResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _StubLLM:
    """Returns a fixed payload and counts invocations."""

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return _StubResponse(self.payload)


@pytest.fixture
def stub_llm(monkeypatch):
    def _install(payload: str) -> _StubLLM:
        stub = _StubLLM(payload)
        for module in (generator_module, reflector_module, test_generator_module):
            monkeypatch.setattr(module, "get_cached_llm", lambda *a, **k: stub)
        return stub

    return _install


CANONICAL_TEST = """
from solution import add


def test_add():
    assert add(2, 3) == 5
"""


@pytest.fixture
def problem_with_tests(tmp_path):
    tests_file = tmp_path / "tests.py"
    tests_file.write_text(CANONICAL_TEST, encoding="utf-8")
    return Problem(
        id="stub_problem",
        prompt="Write add(a, b) returning a + b, and a User model.",
        category="stub",
        canonical_tests_path=str(tests_file),
    )


@pytest.mark.parametrize("max_attempts", [1, 2, 3])
def test_static_failure_path_terminates_at_bound(stub_llm, problem_with_tests, max_attempts):
    """Model always emits v1 syntax -> every attempt dies at static_check."""
    stub_llm(ALWAYS_V1_CODE)

    final = graph_module.run_agent(problem_with_tests, max_attempts=max_attempts)

    assert final.status == "failed_static"
    assert final.attempt_number == max_attempts
    assert len(final.history) == max_attempts
    # Never reached the sandbox on this path.
    assert all(record.execution is None for record in final.history)


@pytest.mark.parametrize("max_attempts", [1, 2, 3])
def test_test_failure_path_terminates_at_bound(stub_llm, problem_with_tests, max_attempts):
    """Model emits clean v2 syntax that is functionally wrong -> dies at execute."""
    stub_llm(ALWAYS_BROKEN_BUT_V2_CODE)

    final = graph_module.run_agent(problem_with_tests, max_attempts=max_attempts)

    assert final.status == "failed_tests"
    assert final.attempt_number == max_attempts
    assert len(final.history) == max_attempts
    assert all(record.execution is not None for record in final.history)
    assert all(not record.execution.passed for record in final.history)


def test_reflector_not_called_after_final_attempt(stub_llm, problem_with_tests):
    """The bound must stop the loop *before* paying for another reflection."""
    stub = stub_llm(ALWAYS_V1_CODE)

    graph_module.run_agent(problem_with_tests, max_attempts=2)

    # 1 test_gen is skipped (canonical tests on disk), so calls are:
    # generate(1) + reflect(1) + generate(2) = 3. No reflect after attempt 2.
    assert stub.calls == 3


def test_success_short_circuits_before_bound(stub_llm, problem_with_tests, monkeypatch):
    """A passing attempt must end the run immediately, not exhaust max_attempts."""
    good_code = """```python
def add(a, b):
    return a + b
```"""
    stub = stub_llm(good_code)

    final = graph_module.run_agent(problem_with_tests, max_attempts=3)

    assert final.status == "passed"
    assert final.attempt_number == 1
    assert len(final.history) == 1
    assert stub.calls == 1
