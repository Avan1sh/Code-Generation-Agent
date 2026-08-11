"""Deterministic static analysis -- no LLM call, runs before we ever pay for a
sandboxed test execution.

Blocking rules (trade-off, stated explicitly): we fail the check on syntax
errors and on Pydantic v1 anti-patterns (the target failure mode for this
whole project), and on pyflakes-detected undefined names (a guaranteed
runtime crash). We do NOT fail on other pyflakes findings such as unused
imports -- those are style noise that would otherwise-correctly solve the
problem, and failing on them would penalize solutions for reasons unrelated
to what we're actually measuring (v1-vs-v2 correctness).
"""

from __future__ import annotations

import ast
import re

from pyflakes.api import check as pyflakes_check
from pyflakes.reporter import Reporter

from agent.state import AgentState, AttemptRecord, StaticCheckResult, StaticIssue

# (pattern, message) -- each pattern targets one specific v1->v2 migration pitfall.
_V1_ANTIPATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"@validator\("), "Uses Pydantic v1 @validator; use @field_validator in v2"),
    (re.compile(r"@root_validator"), "Uses Pydantic v1 @root_validator; use @model_validator in v2"),
    (re.compile(r"\.dict\("), "Uses .dict(); use .model_dump() in v2"),
    (re.compile(r"\.json\("), "Uses .json(); use .model_dump_json() in v2"),
    (re.compile(r"\.parse_obj\("), "Uses .parse_obj(); use .model_validate() in v2"),
    (re.compile(r"\.parse_raw\("), "Uses .parse_raw(); use .model_validate_json() in v2"),
    (re.compile(r"class\s+Config\s*:"), "Uses class-based Config; use model_config = ConfigDict(...) in v2"),
    (re.compile(r"\.parse_file\("), "Uses .parse_file(); read the file and use .model_validate_json() in v2"),
]


class _CollectingReporter(Reporter):
    """Captures pyflakes messages instead of writing them to a stream."""

    def __init__(self) -> None:
        self.messages: list[str] = []

        class _Sink:
            def write(_self, text: str) -> None:  # noqa: N805
                if text.strip():
                    self.messages.append(text.strip())

        sink = _Sink()
        super().__init__(sink, sink)


def _check_syntax(source: str) -> StaticIssue | None:
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return StaticIssue(kind="syntax_error", message=str(exc), line=exc.lineno)
    return None


def _check_pyflakes(source: str) -> list[StaticIssue]:
    reporter = _CollectingReporter()
    pyflakes_check(source, "solution.py", reporter)
    issues: list[StaticIssue] = []
    for msg in reporter.messages:
        kind = "pyflakes_undefined_name" if "undefined name" in msg else "pyflakes_other"
        line = None
        m = re.search(r":(\d+):\d*:", msg)
        if m:
            line = int(m.group(1))
        issues.append(StaticIssue(kind=kind, message=msg, line=line))
    return issues


def _check_v1_antipatterns(source: str) -> list[StaticIssue]:
    issues = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        for pattern, message in _V1_ANTIPATTERNS:
            if pattern.search(line):
                issues.append(StaticIssue(kind="v1_antipattern", message=message, line=lineno))
    return issues


def run_static_check(source: str) -> StaticCheckResult:
    syntax_issue = _check_syntax(source)
    if syntax_issue is not None:
        # Don't bother running pyflakes/antipattern scan on unparseable code.
        return StaticCheckResult(passed=False, issues=[syntax_issue])

    issues = _check_pyflakes(source) + _check_v1_antipatterns(source)
    blocking = [i for i in issues if i.kind in ("v1_antipattern", "pyflakes_undefined_name")]
    return StaticCheckResult(passed=len(blocking) == 0, issues=issues)


def static_check_node(state: AgentState) -> dict:
    code = state.generated_code or ""
    result = run_static_check(code)

    update: dict = {"static_check_result": result}

    if result.passed:
        # The executor commits this attempt's history record instead -- it will
        # have the execution outcome attached. Committing here too would
        # double-count the attempt.
        return update

    # Static failure: the attempt ends here without reaching the sandbox, so
    # this node owns the history record. execution stays None, which is how
    # analyze.py distinguishes static rejections from test failures.
    update["history"] = [
        AttemptRecord(
            attempt_number=state.attempt_number,
            code=code,
            static_check=result,
            execution=None,
            reflection=state.reflection,
        )
    ]

    if state.attempt_number >= state.max_attempts:
        # Attempt ceiling reached on the static-check path -- terminate here
        # rather than spending a sandbox run on code we already know is broken.
        update["status"] = "failed_static"

    return update
