"""pass@1 baseline -- the floor the self-correction loop must beat.

This is the honest comparison point. It uses the SAME system prompt, the SAME
temperature (0.0), and the SAME model as attempt 1 of the agent
(agent/nodes/generator.py). The only difference is that nothing happens after
the first generation: no static check, no reflection, no retry.

Because attempt 1 of the agent is prompt-identical to this, any gap between the
two is attributable to the correction loop rather than to prompt differences.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from agent.llm import get_cached_llm, strip_code_fences
from agent.nodes.generator import SYSTEM_PROMPT
from agent.sandbox import run_tests_in_sandbox
from agent.state import ExecutionResult, Problem


class BaselineResult(BaseModel):
    problem_id: str
    method: str
    passed: bool
    llm_calls: int
    code: str
    execution: ExecutionResult | None = None
    # best_of_n only; None for single_shot.
    samples_passed: int | None = None


def run_single_shot(problem: Problem, test_code: str) -> BaselineResult:
    llm = get_cached_llm(temperature=0.0)
    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=problem.prompt),
        ]
    )
    code = strip_code_fences(response.content)
    execution = run_tests_in_sandbox(solution_code=code, test_code=test_code)

    return BaselineResult(
        problem_id=problem.id,
        method="single_shot",
        passed=execution.passed,
        llm_calls=1,
        code=code,
        execution=execution,
    )
