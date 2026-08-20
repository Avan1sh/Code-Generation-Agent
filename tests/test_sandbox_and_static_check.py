"""Coverage for the two deterministic, no-LLM-required pieces of the pipeline.

These run without any API key -- they're the part of the system whose
correctness we can actually assert in CI, as opposed to LLM output quality
which can only be measured via eval/run_eval.py against real problems.
"""

from __future__ import annotations

import pytest

from agent.nodes.static_check import run_static_check
from agent.sandbox import (
    SandboxHealthError,
    run_tests_in_sandbox,
    verify_sandbox_health,
)

# ---------------------------------------------------------------------------
# static_check
# ---------------------------------------------------------------------------

V1_VALIDATOR_SNIPPET = """
from pydantic import BaseModel, validator


class User(BaseModel):
    name: str

    @validator("name")
    def check_name(cls, v):
        return v
"""

V2_VALIDATOR_SNIPPET = """
from pydantic import BaseModel, field_validator


class User(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def check_name(cls, v):
        return v
"""

V1_DICT_SNIPPET = """
from pydantic import BaseModel


class User(BaseModel):
    name: str


def serialize(u: User) -> dict:
    return u.dict()
"""

V1_CONFIG_SNIPPET = """
from pydantic import BaseModel


class User(BaseModel):
    name: str

    class Config:
        frozen = True
"""

SYNTAX_ERROR_SNIPPET = "def broken(:\n    pass"

UNDEFINED_NAME_SNIPPET = """
from pydantic import BaseModel


class User(BaseModel):
    name: str

    def greet(self):
        return does_not_exist(self.name)
"""

UNUSED_IMPORT_SNIPPET = """
import os
from pydantic import BaseModel


class User(BaseModel):
    name: str
"""


def test_v1_validator_fails():
    result = run_static_check(V1_VALIDATOR_SNIPPET)
    assert not result.passed
    assert any(i.kind == "v1_antipattern" for i in result.issues)


def test_v2_validator_passes():
    result = run_static_check(V2_VALIDATOR_SNIPPET)
    assert result.passed


def test_v1_dict_call_fails():
    result = run_static_check(V1_DICT_SNIPPET)
    assert not result.passed
    assert any("model_dump" in i.message for i in result.issues)


def test_v1_class_config_fails():
    result = run_static_check(V1_CONFIG_SNIPPET)
    assert not result.passed
    assert any("ConfigDict" in i.message for i in result.issues)


def test_syntax_error_fails_and_short_circuits():
    result = run_static_check(SYNTAX_ERROR_SNIPPET)
    assert not result.passed
    assert len(result.issues) == 1
    assert result.issues[0].kind == "syntax_error"


def test_undefined_name_fails():
    result = run_static_check(UNDEFINED_NAME_SNIPPET)
    assert not result.passed
    assert any(i.kind == "pyflakes_undefined_name" for i in result.issues)


def test_unused_import_does_not_fail():
    result = run_static_check(UNUSED_IMPORT_SNIPPET)
    assert result.passed
    assert any(i.kind == "pyflakes_other" for i in result.issues)


# ---------------------------------------------------------------------------
# sandbox
# ---------------------------------------------------------------------------

PASSING_SOLUTION = """
from pydantic import BaseModel


class User(BaseModel):
    name: str
"""

PASSING_TEST = """
from solution import User


def test_user_holds_name():
    u = User(name="ada")
    assert u.name == "ada"
"""

FAILING_TEST = """
from solution import User


def test_user_wrong():
    u = User(name="ada")
    assert u.name == "not-ada"
"""

INFINITE_LOOP_SOLUTION = """
def never_returns():
    while True:
        pass
"""

INFINITE_LOOP_TEST = """
from solution import never_returns


def test_hangs():
    never_returns()
"""


def test_sandbox_passing_case():
    result = run_tests_in_sandbox(PASSING_SOLUTION, PASSING_TEST, timeout_sec=10)
    assert result.passed
    assert not result.timed_out
    assert result.return_code == 0


def test_sandbox_failing_case():
    result = run_tests_in_sandbox(PASSING_SOLUTION, FAILING_TEST, timeout_sec=10)
    assert not result.passed
    assert not result.timed_out
    assert result.return_code != 0


def test_sandbox_kills_infinite_loop():
    result = run_tests_in_sandbox(INFINITE_LOOP_SOLUTION, INFINITE_LOOP_TEST, timeout_sec=3)
    assert not result.passed
    assert result.timed_out


# ---------------------------------------------------------------------------
# health check -- runs on every platform, including Windows where the POSIX
# limits are inactive. On Windows it verifies the sandbox can run pydantic at
# all; on POSIX it additionally verifies the resource ceilings are not so tight
# that they reject valid code.
# ---------------------------------------------------------------------------


def test_health_check_passes_on_this_platform():
    verify_sandbox_health()


def test_health_check_raises_when_limits_are_unworkable():
    """An absurdly small ceiling must produce a loud, self-describing error.

    This is the failure the check exists to catch: without it, limits too tight
    for the interpreter would make every problem fail and the eval would report
    0 passes that look like model failure.
    """
    with pytest.raises(SandboxHealthError) as exc:
        # A zero budget is the only deterministic choice: an earlier version used
        # 1 second and passed only on a cold machine, silently going green on a
        # warm one. Any real process takes more than zero seconds.
        verify_sandbox_health(timeout_sec=0)

    message = str(exc.value)
    assert "misconfiguration" in message
    assert "not a code-generation failure" in message


def test_health_check_returns_probe_duration_when_healthy():
    """The healthy path must return a measured duration, not None.

    Regression guard: an early return placed above the raise once disabled the
    failure branch entirely, so the check reported healthy no matter what. A
    disabled guard is worse than no guard, because it is trusted.
    """
    seconds = verify_sandbox_health()
    assert isinstance(seconds, float)
    assert seconds > 0
