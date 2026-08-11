"""Code generation node.

On attempt 1 this is a plain zero-shot generation -- identical in prompt and
temperature to baselines/single_shot.py, on purpose. If the first attempt here
differed from the baseline, any measured improvement would confound "the loop
helped" with "the retry prompt was just better", and the comparison would be
worthless.

On attempts 2+ the prompt additionally carries the previous code, the concrete
failure evidence, and the reflector's diagnosis.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import get_cached_llm, strip_code_fences
from agent.state import AgentState

SYSTEM_PROMPT = """You are an expert Python developer writing Pydantic v2 code.

Rules:
- Target Pydantic v2 ONLY. v1 syntax will fail: use @field_validator (not @validator),
  @model_validator (not @root_validator), model_config = ConfigDict(...) (not class Config),
  .model_dump() (not .dict()), .model_dump_json() (not .json()),
  .model_validate() (not .parse_obj()), .model_validate_json() (not .parse_raw()).
- Output ONE Python code block containing the complete module. No explanation outside it.
- Include every import the module needs.
- Use exactly the class and function names the task specifies."""

RETRY_TEMPLATE = """Your previous attempt failed. Fix it.

--- TASK ---
{prompt}

--- YOUR PREVIOUS CODE ---
```python
{previous_code}
```

--- FAILURE EVIDENCE ---
{failure_evidence}

--- DIAGNOSIS ---
{reflection}

Output the complete corrected module as one Python code block."""


def _format_failure_evidence(state: AgentState) -> str:
    parts: list[str] = []

    if state.static_check_result and not state.static_check_result.passed:
        parts.append("Static check failed:")
        for issue in state.static_check_result.issues:
            if issue.kind in ("v1_antipattern", "syntax_error", "pyflakes_undefined_name"):
                loc = f"line {issue.line}: " if issue.line else ""
                parts.append(f"  - {loc}{issue.message}")

    if state.execution_result and not state.execution_result.passed:
        if state.execution_result.timed_out:
            parts.append("Test execution timed out (likely an infinite loop).")
        else:
            parts.append("Test failures:")
            # Truncated: mid-tier models degrade on very long contexts, and
            # pytest output is mostly boilerplate. The tail holds the summary.
            tail = state.execution_result.stdout[-2000:]
            parts.append(tail)

    return "\n".join(parts) if parts else "(no evidence captured)"


def generator_node(state: AgentState) -> dict:
    llm = get_cached_llm(temperature=0.0)
    attempt = state.attempt_number + 1

    if attempt == 1:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=state.problem.prompt),
        ]
    else:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=RETRY_TEMPLATE.format(
                    prompt=state.problem.prompt,
                    previous_code=state.generated_code or "",
                    failure_evidence=_format_failure_evidence(state),
                    reflection=state.reflection or "(no diagnosis available)",
                )
            ),
        ]

    response = llm.invoke(messages)
    code = strip_code_fences(response.content)

    return {
        "generated_code": code,
        "attempt_number": attempt,
        # Cleared so a stale result from the prior attempt can never be read as
        # this attempt's outcome by a downstream node or the router.
        # `reflection` is deliberately NOT cleared: it holds the diagnosis that
        # guided this attempt, and the attempt's history record captures it as
        # such (see AttemptRecord.reflection).
        "static_check_result": None,
        "execution_result": None,
    }
