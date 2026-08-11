"""Graph wiring.

    test_gen -> generate -> static_check --pass--> execute --pass--> END
                    ^            |                     |
                    |         fail|                fail |
                    |            v                     v
                    +--------- reflect <---------------+
                                 (only if attempts remain)

Termination, stated precisely, because "the loop is bounded" is the claim most
worth being able to defend:

  1. Every failure path is guarded by a node-level check of
     `attempt_number >= max_attempts` (in static_check_node and executor_node),
     which sets a terminal status. The routers below only read that status --
     they never decide termination themselves.
  2. `attempt_number` is incremented by generator_node on every pass and is
     never decremented anywhere, so the guard in (1) is guaranteed to fire
     within max_attempts generations regardless of what the model outputs.
  3. `recursion_limit` on invoke is a backstop only, not the guarantee. It is
     deliberately set above the worst-case node count so that hitting it means
     a wiring bug, not normal operation -- and it raises GraphRecursionError
     (a crash) rather than producing a clean terminal state, which is why it
     must not be the primary mechanism.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.nodes.executor import executor_node
from agent.nodes.generator import generator_node
from agent.nodes.reflector import reflector_node
from agent.nodes.static_check import static_check_node
from agent.nodes.test_generator import test_generator_node
from agent.state import AgentState, Problem

# Worst case per attempt: generate -> static_check -> execute -> reflect = 4 nodes,
# plus the one-time test_gen node, plus slack for LangGraph's internal steps.
_NODES_PER_ATTEMPT = 4
_RECURSION_SLACK = 10


def _route_after_static_check(state: AgentState) -> str:
    if state.status != "in_progress":
        return END
    if state.static_check_result and state.static_check_result.passed:
        return "execute"
    return "reflect"


def _route_after_execute(state: AgentState) -> str:
    if state.status != "in_progress":
        return END
    return "reflect"


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("test_gen", test_generator_node)
    builder.add_node("generate", generator_node)
    builder.add_node("static_check", static_check_node)
    builder.add_node("execute", executor_node)
    builder.add_node("reflect", reflector_node)

    builder.set_entry_point("test_gen")
    # test_gen runs once, before the loop -- regenerating tests per attempt
    # would let the success criterion drift under a failing solution.
    builder.add_edge("test_gen", "generate")
    builder.add_edge("generate", "static_check")

    builder.add_conditional_edges(
        "static_check",
        _route_after_static_check,
        {"execute": "execute", "reflect": "reflect", END: END},
    )
    builder.add_conditional_edges(
        "execute",
        _route_after_execute,
        {"reflect": "reflect", END: END},
    )
    builder.add_edge("reflect", "generate")

    return builder.compile()


def run_agent(problem: Problem, max_attempts: int = 3) -> AgentState:
    graph = build_graph()
    initial = AgentState(problem=problem, max_attempts=max_attempts)

    final = graph.invoke(
        initial,
        config={"recursion_limit": max_attempts * _NODES_PER_ATTEMPT + _RECURSION_SLACK},
    )
    # LangGraph returns the state as a dict; re-validate into the typed model so
    # callers always get AgentState, never a bare dict.
    return AgentState.model_validate(final)
