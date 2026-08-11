"""pass@N ORACLE ceiling -- deliberately not a fair baseline, and labelled so.

This draws N independent samples at temperature > 0 and reports whether ANY of
them passed. That requires knowing which sample passed, which at inference time
would mean already having the tests -- so this is an upper bound on what
resampling could achieve with a perfect selector, not a deployable strategy.

Why include it anyway: it is compute-matched to the self-correction loop. N is
set to the agent's max_attempts, so both spend a comparable number of
generation calls. That makes the interesting question answerable -- given the
same budget, does *directed* correction (reflect on the actual error) beat
*undirected* resampling (roll the dice again)? If self-correct lands near
pass@N, the loop is extracting most of the available headroom. If it lands near
single-shot, the reflection step is not earning its cost.

Temperature: sampling at 0.0 would return N near-identical completions and the
ceiling would collapse onto single_shot, making the comparison meaningless.
0.8 is used to get genuine diversity. Trade-off: higher temperature also raises
the variance of any individual sample's quality.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import get_llm, strip_code_fences
from agent.nodes.generator import SYSTEM_PROMPT
from agent.sandbox import run_tests_in_sandbox
from agent.state import Problem
from baselines.single_shot import BaselineResult

SAMPLING_TEMPERATURE = 0.8


def run_best_of_n(problem: Problem, test_code: str, n: int = 3) -> BaselineResult:
    if n < 1:
        raise ValueError("n must be >= 1")

    llm = get_llm(temperature=SAMPLING_TEMPERATURE)

    samples_passed = 0
    first_passing_code: str | None = None
    last_code = ""
    last_execution = None

    # Bounded by n, which is supplied by the caller -- no early-exit on success,
    # because samples_passed (how many of N worked) is itself a useful signal
    # about how close the model is to getting the problem right by chance.
    for _ in range(n):
        response = llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=problem.prompt),
            ]
        )
        code = strip_code_fences(response.content)
        execution = run_tests_in_sandbox(solution_code=code, test_code=test_code)

        last_code = code
        last_execution = execution
        if execution.passed:
            samples_passed += 1
            if first_passing_code is None:
                first_passing_code = code

    return BaselineResult(
        problem_id=problem.id,
        method="best_of_n",
        passed=samples_passed > 0,
        llm_calls=n,
        code=first_passing_code or last_code,
        execution=last_execution,
        samples_passed=samples_passed,
    )
