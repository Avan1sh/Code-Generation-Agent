"""Typed state for the self-correcting agent graph.

Everything here is a Pydantic v2 model, not a dict-with-string-keys. This is a
deliberate constraint: the graph state must be as type-safe as the code it is
asking the model to write.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# Terminal/​in-progress states. "passed" and the "failed_*" variants are terminal;
# a node reaching a terminal state must not route anywhere but END.
Status = Literal[
    "in_progress",
    "passed",
    "failed_static",
    "failed_tests",
]


class Problem(BaseModel):
    """A single eval-set problem, or an ad-hoc prompt built by solve.py."""

    id: str
    prompt: str
    category: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    # None for ad-hoc prompts (solve.py) -- in that case test_generator falls
    # back to an LLM-written test suite instead of a hand-verified one. See
    # agent/nodes/test_generator.py for why that distinction matters.
    canonical_tests_path: str | None = None


class StaticIssue(BaseModel):
    kind: Literal["syntax_error", "pyflakes_undefined_name", "pyflakes_other", "v1_antipattern"]
    message: str
    line: int | None = None


class StaticCheckResult(BaseModel):
    passed: bool
    issues: list[StaticIssue] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    passed: bool
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_sec: float


class AttemptRecord(BaseModel):
    """One full pass through generate -> check -> (test) for the eval log.

    `execution` is None when the attempt was rejected by the static check and
    never reached the sandbox. `reflection` is the diagnosis that *guided* this
    attempt (None on attempt 1), not a diagnosis of it -- that lets analysis ask
    "did this diagnosis lead to a fix?" by looking at the next record.
    """

    attempt_number: int
    code: str
    static_check: StaticCheckResult | None = None
    execution: ExecutionResult | None = None
    reflection: str | None = None


class AgentState(BaseModel):
    problem: Problem

    # Cost-vs-quality trade-off: higher max_attempts raises the pass rate ceiling
    # but linearly raises LLM spend and sandbox time per problem. 3 is the default
    # balance; eval/run_eval.py and solve.py both let this be overridden per run
    # so the trade-off is a knob, not a hidden constant.
    max_attempts: int = 3
    attempt_number: int = 0

    generated_code: str | None = None
    test_code: str | None = None
    static_check_result: StaticCheckResult | None = None
    execution_result: ExecutionResult | None = None
    reflection: str | None = None

    # Reducer so each node appends rather than overwrites -- LangGraph merges
    # partial node returns into state, and list fields need an explicit reducer
    # or a later node's return would clobber history instead of extending it.
    history: Annotated[list[AttemptRecord], operator.add] = Field(default_factory=list)

    status: Status = "in_progress"
