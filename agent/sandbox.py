"""Runs LLM-generated code inside a resource-limited subprocess.

Hard constraint: never exec()/eval() generated code in-process, even for a
throwaway check. Everything goes through `subprocess.run` against a pytest
invocation in a scratch directory.

Trade-off (documented, not silently assumed): CPU-time and memory ceilings via
`resource.setrlimit` are POSIX-only -- the `resource` module does not exist on
Windows. On Windows this sandbox falls back to wall-clock timeout only, with no
memory/CPU ceiling and no network isolation. That is a real gap, not a
theoretical one: a generated solution with a runaway allocation or an infinite
CPU-bound loop will be killed by the timeout, but one that opens a socket or
allocates memory more slowly than the CPU limit would have caught it will not
be stopped by anything here. For a stricter guarantee, run this in WSL/Linux
(where the POSIX limits activate) or a container. This is called out again in
README.md's Limitations section.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from agent.state import ExecutionResult

_IS_POSIX = sys.platform != "win32"

if _IS_POSIX:
    import resource


class SandboxHealthError(RuntimeError):
    """Raised when the sandbox cannot run known-good code under its own limits."""


# RLIMIT_AS caps *virtual address space*, not resident memory. CPython plus
# pydantic-core (Rust) reserve considerably more address space than they ever
# make resident, so a ceiling tuned to "how much memory should a solution need"
# will reject perfectly good solutions. The default below is therefore
# deliberately generous: it exists to stop unbounded allocation, not to enforce
# a tight budget.
#
# This number is NOT tuned from measurement on this machine -- the POSIX path
# could not be executed here (Windows). That is precisely why
# verify_sandbox_health() exists: rather than trusting the constant, the value
# is validated at startup on whatever platform actually runs it, and a bad
# value fails loudly instead of silently failing every solution.
# Overridable because the right value depends on the host, not on the code: a
# ceiling ABOVE the container's own memory budget protects nothing. On a
# 512MB instance a 2048MB RLIMIT_AS lets the child grow until the *container*
# is OOM-killed, taking the server with it -- the limit has to sit below the
# container budget to do any work at all.
DEFAULT_MEMORY_MB = int(os.environ.get("SANDBOX_MEMORY_MB", "2048"))

# Wall-clock ceiling for one test run. 10s is ample on a developer machine, and
# far too tight on constrained shared hosting: Render's free tier allocates a
# fraction of a CPU, where interpreter startup plus a pydantic import alone can
# exceed it. When that happens every attempt reports timed_out and the run looks
# like the model wrote an infinite loop, which is the exact class of
# misattribution this project tries to eliminate. Overridable per environment.
DEFAULT_TIMEOUT_SEC = int(os.environ.get("SANDBOX_TIMEOUT_SEC", "10"))


def _limit_resources(memory_mb: int, cpu_sec: int):
    """Returns a preexec_fn that caps address space and CPU time. POSIX only.

    Note: preexec_fn is not thread-safe (it runs between fork and exec). The
    eval harness is single-threaded, so this is safe here; parallelising
    run_eval.py would require revisiting this.
    """

    def _apply() -> None:
        mem_bytes = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_sec, cpu_sec))
        # Belt-and-suspenders against fork bombs. RLIMIT_NPROC is per-UID and
        # checked at fork time, so this constrains what the child can spawn
        # without affecting already-running processes owned by the same user.
        resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))

    return _apply


# Known-good code used only by verify_sandbox_health. Exercises the real
# dependency (pydantic) rather than bare Python, since importing pydantic-core
# is the step most likely to breach an address-space ceiling.
_HEALTH_SOLUTION = """
from pydantic import BaseModel, field_validator


class _Health(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()
"""

_HEALTH_TEST = """
from solution import _Health


def test_health():
    assert _Health(value="  ok  ").value == "ok"
"""


def verify_sandbox_health(timeout_sec: int = 60, memory_mb: int = DEFAULT_MEMORY_MB) -> float:
    """Runs known-good code under the configured limits. Raises if it fails.

    Why this exists: if the resource ceilings are set too tight for the
    interpreter itself, every solution fails for reasons that have nothing to
    do with the solution. The eval would report zero passes across the board
    and it would look like a model failure rather than a sandbox
    misconfiguration. Checking once at startup makes that failure mode loud and
    self-describing instead of silent and misattributed.
    """
    result = run_tests_in_sandbox(
        _HEALTH_SOLUTION, _HEALTH_TEST, timeout_sec=timeout_sec, memory_mb=memory_mb
    )
    if not result.passed:
        raise SandboxHealthError(
            "Sandbox failed to run known-good pydantic code under its own limits.\n"
            f"  platform: {sys.platform}\n"
            f"  POSIX resource limits active: {_IS_POSIX}\n"
            f"  memory_mb: {memory_mb}, timeout_sec: {timeout_sec}\n"
            f"  timed_out: {result.timed_out}, return_code: {result.return_code}\n"
            "This is a sandbox misconfiguration, not a code-generation failure. "
            "If POSIX limits are active, memory_mb is the most likely cause -- "
            "RLIMIT_AS caps virtual address space, which CPython reserves far more "
            "of than it makes resident.\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )

    # Returned so callers can compare it against the configured timeout: a probe
    # that consumes most of the budget means the ceiling is about to start
    # rejecting valid code on this hardware.
    return result.duration_sec


def run_tests_in_sandbox(
    solution_code: str,
    test_code: str,
    timeout_sec: int | None = None,
    memory_mb: int = DEFAULT_MEMORY_MB,
) -> ExecutionResult:
    """Writes solution_code + test_code to a scratch dir and runs pytest on them.

    test_code must `from solution import ...` -- the solution module name is
    fixed so every problem's canonical tests.py can rely on it.
    """
    if timeout_sec is None:
        timeout_sec = DEFAULT_TIMEOUT_SEC
    with tempfile.TemporaryDirectory(prefix="selfcorrect_sandbox_") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "solution.py").write_text(solution_code, encoding="utf-8")
        (tmp_path / "test_solution.py").write_text(test_code, encoding="utf-8")

        cmd = [sys.executable, "-m", "pytest", "test_solution.py", "-q", "--no-header"]
        kwargs: dict = {}
        if _IS_POSIX:
            # cpu_sec is separate from the wall-clock timeout below: CPU time
            # excludes time spent blocked (e.g. sleeping), wall-clock does not.
            kwargs["preexec_fn"] = _limit_resources(memory_mb, cpu_sec=timeout_sec)

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                **kwargs,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - start
            return ExecutionResult(
                passed=False,
                return_code=-1,
                stdout=(exc.stdout or ""),
                stderr=(exc.stderr or "") + "\n[sandbox] killed after timeout",
                timed_out=True,
                duration_sec=duration,
            )

        duration = time.monotonic() - start
        return ExecutionResult(
            passed=proc.returncode == 0,
            return_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            timed_out=False,
            duration_sec=duration,
        )
