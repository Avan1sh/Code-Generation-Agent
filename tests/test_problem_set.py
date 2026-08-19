"""Validates the eval set itself.

The point: if a problem's canonical tests were broken or the task were
impossible as written, every method would score 0 on it and the eval would look
like a model failure rather than an authoring bug. Running each hand-written
reference solution through the same sandbox the agent uses rules that out.

This also enforces that reference solutions are genuinely v2 -- if a reference
tripped the v1 anti-pattern detector, the static check would reject a correct
answer and the eval would be measuring the detector's false positives.

No API key required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.nodes.static_check import run_static_check
from agent.sandbox import run_tests_in_sandbox
from problems import load_problems, problem_dir

PROBLEMS = load_problems()


def test_problem_set_is_non_empty():
    assert len(PROBLEMS) == 30


@pytest.mark.parametrize("problem", PROBLEMS, ids=lambda p: p.id)
def test_reference_solution_passes_canonical_tests(problem):
    reference = problem_dir(problem.id) / "reference.py"
    assert reference.exists(), f"{problem.id} has no reference.py"

    tests = Path(problem.canonical_tests_path).read_text(encoding="utf-8")
    result = run_tests_in_sandbox(
        solution_code=reference.read_text(encoding="utf-8"),
        test_code=tests,
        timeout_sec=30,
    )
    assert result.passed, (
        f"{problem.id}: reference solution failed its own tests.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.parametrize("problem", PROBLEMS, ids=lambda p: p.id)
def test_reference_solution_passes_static_check(problem):
    reference = problem_dir(problem.id) / "reference.py"
    result = run_static_check(reference.read_text(encoding="utf-8"))
    assert result.passed, (
        f"{problem.id}: reference solution tripped the static check -- "
        f"this is a false positive in the detector.\n"
        f"{[i.message for i in result.issues]}"
    )


@pytest.mark.parametrize("problem", PROBLEMS, ids=lambda p: p.id)
def test_prompt_does_not_leak_the_answer(problem):
    """The prompt states requirements, not the v2 API names to use.

    If prompts named the exact v2 decorators, the v1-default failure mode would
    never surface and the eval would measure instruction-following, not
    knowledge of the v2 API.
    """
    leaked = [
        "field_validator",
        "model_validator",
        "ConfigDict",
        "model_dump",
        "model_validate",
        "computed_field",
        "field_serializer",
        "TypeAdapter",
        "model_copy",
        "model_construct",
        "model_json_schema",
        "model_rebuild",
        "RootModel",
        "AliasChoices",
        "validate_default",
        "serialization_alias",
        "validation_alias",
        "default_factory",
        "use_enum_values",
        "min_length",
        "max_length",
        "exclude_none",
    ]
    found = [name for name in leaked if name in problem.prompt]
    assert not found, f"{problem.id} prompt leaks v2 API names: {found}"
