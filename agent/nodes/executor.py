"""Runs the generated solution against the test suite in the sandbox, and is
the single place where an attempt gets committed to history.

Termination logic lives here, not in the router: this node compares
attempt_number against max_attempts itself and writes a terminal status. The
conditional edge in graph.py only dispatches on that status. That keeps the
"stop after N" guarantee in one place per failure path and makes it independent
of anything the model does.
"""

from __future__ import annotations

from agent.sandbox import run_tests_in_sandbox
from agent.state import AgentState, AttemptRecord


def executor_node(state: AgentState) -> dict:
    result = run_tests_in_sandbox(
        solution_code=state.generated_code or "",
        test_code=state.test_code or "",
    )

    record = AttemptRecord(
        attempt_number=state.attempt_number,
        code=state.generated_code or "",
        static_check=state.static_check_result,
        execution=result,
        reflection=state.reflection,
    )

    update: dict = {"execution_result": result, "history": [record]}

    if result.passed:
        update["status"] = "passed"
    elif state.attempt_number >= state.max_attempts:
        update["status"] = "failed_tests"

    return update
