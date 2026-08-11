"""POSIX-only sandbox tests: the resource-limit path.

These are skipped on Windows, where `resource.setrlimit` does not exist and the
sandbox degrades to wall-clock timeout only (see agent/sandbox.py). That means
on Windows the limits below are NOT enforced and NOT tested -- which is exactly
why this file must exist and must be run on Linux before any claim is made
about memory or CPU ceilings holding.

The first test is the important one. A resource limit that is too tight is not
a safe default, it is a broken sandbox: if RLIMIT_AS is smaller than what
CPython plus pydantic-core need for their virtual address space, EVERY run
fails, the whole eval reports zero passes, and the failure looks like a model
problem rather than a sandbox misconfiguration.
"""

from __future__ import annotations

import sys

import pytest

from agent.sandbox import DEFAULT_MEMORY_MB, run_tests_in_sandbox, verify_sandbox_health

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="resource.setrlimit is POSIX-only; the sandbox has no memory/CPU ceiling on Windows",
)

PYDANTIC_SOLUTION = """
from pydantic import BaseModel, field_validator


class User(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()
"""

PYDANTIC_TEST = """
from solution import User


def test_user():
    assert User(name="  ada  ").name == "ada"
"""

MEMORY_HOG_SOLUTION = """
def allocate():
    # Deliberately exceeds any sane per-run memory ceiling.
    chunks = []
    while True:
        chunks.append(bytearray(50 * 1024 * 1024))
"""

MEMORY_HOG_TEST = """
from solution import allocate


def test_allocates():
    allocate()
"""

CPU_HOG_SOLUTION = """
def burn():
    x = 0
    while True:
        x += 1
"""

CPU_HOG_TEST = """
from solution import burn


def test_burns():
    burn()
"""


def test_normal_run_survives_the_limits():
    """The limits must not break a legitimate pydantic solution.

    This is the regression guard for "the sandbox is too strict to run anything".
    """
    result = run_tests_in_sandbox(PYDANTIC_SOLUTION, PYDANTIC_TEST, timeout_sec=30)
    assert result.passed, (
        "A valid pydantic solution failed under the resource limits -- the limits "
        f"are too tight, not the solution.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_memory_hog_is_contained():
    """Runaway allocation must be stopped, and not by the wall clock.

    A generous timeout is used so that if this passes it is the memory ceiling
    doing the work, not the timeout masking an unenforced limit.
    """
    result = run_tests_in_sandbox(
        MEMORY_HOG_SOLUTION, MEMORY_HOG_TEST, timeout_sec=60, memory_mb=DEFAULT_MEMORY_MB
    )
    assert not result.passed
    assert not result.timed_out, "killed by the wall clock, so the memory ceiling is not doing anything"


def test_health_check_passes_under_posix_limits():
    """The startup guard must agree that the limits are workable on this platform."""
    verify_sandbox_health()


def test_cpu_hog_is_contained():
    """An infinite CPU-bound loop must hit the CPU ceiling before the wall clock."""
    result = run_tests_in_sandbox(CPU_HOG_SOLUTION, CPU_HOG_TEST, timeout_sec=5)
    assert not result.passed
