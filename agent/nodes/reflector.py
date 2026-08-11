"""Diagnoses why the last attempt failed, before the next generation.

One LLM call, no loop of its own. The reflector is prompted to produce a
diagnosis and a fix direction, explicitly NOT code -- separating "what went
wrong" from "write it again" is the whole hypothesis being tested here. If this
node emitted code directly it would just be a second generator, and the eval
would no longer isolate whether reflection contributes anything.

Cost trade-off: this adds one extra LLM call per failed attempt, so a 3-attempt
run costs up to 5 calls instead of 3. That is the price of the intervention
being measured; eval/run_eval.py records call counts so the cost side of the
trade-off is visible in the results rather than assumed away.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import get_cached_llm
from agent.state import AgentState

REFLECT_SYSTEM_PROMPT = """You diagnose failing Python code. You do NOT write code.

Given a task, a failed attempt, and the failure output, respond with at most 5 lines:
1. The specific root cause (name the exact construct that is wrong).
2. The concrete change needed to fix it.

Be specific about Pydantic v2 API names. Do not output a code block."""

REFLECT_TEMPLATE = """--- TASK ---
{prompt}

--- FAILED CODE ---
```python
{code}
```

--- FAILURE OUTPUT ---
{evidence}

Diagnose the root cause and state the fix."""


def _evidence(state: AgentState) -> str:
    parts: list[str] = []

    if state.static_check_result and not state.static_check_result.passed:
        for issue in state.static_check_result.issues:
            if issue.kind in ("v1_antipattern", "syntax_error", "pyflakes_undefined_name"):
                loc = f"line {issue.line}: " if issue.line else ""
                parts.append(f"{loc}{issue.message}")

    if state.execution_result and not state.execution_result.passed:
        if state.execution_result.timed_out:
            parts.append("Execution timed out.")
        else:
            parts.append(state.execution_result.stdout[-2000:])
            if state.execution_result.stderr.strip():
                parts.append(state.execution_result.stderr[-1000:])

    return "\n".join(parts) if parts else "(no evidence captured)"


def reflector_node(state: AgentState) -> dict:
    llm = get_cached_llm(temperature=0.0)
    response = llm.invoke(
        [
            SystemMessage(content=REFLECT_SYSTEM_PROMPT),
            HumanMessage(
                content=REFLECT_TEMPLATE.format(
                    prompt=state.problem.prompt,
                    code=state.generated_code or "",
                    evidence=_evidence(state),
                )
            ),
        ]
    )
    return {"reflection": response.content.strip()}
