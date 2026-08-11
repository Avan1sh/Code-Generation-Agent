"""Supplies the test suite the generated solution is judged against.

Trade-off, and the most important methodological decision in the project:

  - For eval-set problems, tests are HAND-WRITTEN and loaded from disk. The
    pass/fail signal for a measured benchmark must not itself depend on LLM
    output quality. If the model wrote its own tests, a weak model could write
    weak tests, "pass" them, and inflate the score -- the metric would measure
    the model's self-agreement, not correctness.

  - For ad-hoc prompts via solve.py (no canonical tests exist), tests are
    LLM-generated. This is strictly less trustworthy and is never used for any
    number reported in the README. It exists so the agent is usable on new
    problems, not so it can grade itself.

The node runs once per problem, not once per attempt -- see graph.py, where it
sits before the retry loop. Regenerating tests per attempt would let the target
move under a failing solution.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import get_cached_llm, strip_code_fences
from agent.state import AgentState

TEST_SYSTEM_PROMPT = """You write pytest test suites.

Rules:
- The module under test is always imported as: from solution import <names>
- Use plain `assert` statements and pytest.raises for error cases.
- Test the observable behaviour the task describes, including at least one
  invalid-input case.
- Output ONE Python code block. No explanation outside it."""


def test_generator_node(state: AgentState) -> dict:
    canonical = state.problem.canonical_tests_path
    if canonical:
        test_code = Path(canonical).read_text(encoding="utf-8")
        return {"test_code": test_code}

    llm = get_cached_llm(temperature=0.0)
    response = llm.invoke(
        [
            SystemMessage(content=TEST_SYSTEM_PROMPT),
            HumanMessage(content=f"Write a pytest suite for this task:\n\n{state.problem.prompt}"),
        ]
    )
    return {"test_code": strip_code_fences(response.content)}
