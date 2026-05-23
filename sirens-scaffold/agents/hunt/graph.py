"""Assemble the Hunt-swarm LangGraph.

    hypothesis_planner → (hypotheses?) → escalator       (empty report)
                       ↓
                     query_writer → hunter → triage → escalator
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.hunt.dispatch import HuntDispatch, StubDispatch
from agents.hunt.nodes import (
    DEFAULT_ESCALATION_THRESHOLD,
    make_escalator,
    make_hunter,
    make_hypothesis_planner,
    make_query_writer,
    make_triage,
)
from agents.hunt.state import HuntState


def _route_after_planner(state: HuntState) -> str:
    """If the planner produced zero hypotheses, skip straight to escalator.

    A zero-hypothesis state means the tasking wasn't a real hunt — the
    escalator still emits a typed (empty) report so the caller always gets
    a shape-valid result.
    """
    if not state.get("hypotheses"):
        return "escalator"
    return "query_writer"


def build_hunt_graph(
    dispatch: HuntDispatch | None = None,
    escalation_threshold: int = DEFAULT_ESCALATION_THRESHOLD,
):
    """Return a compiled LangGraph app for the Hunt swarm.

    Pass a `LiveDispatch` (Phase 4.1) for real MCP wiring, or leave as None
    to use `StubDispatch` for unit tests and demos without the stack.
    """
    dispatch = dispatch or StubDispatch()
    graph = StateGraph(HuntState)

    graph.add_node("hypothesis_planner", make_hypothesis_planner(dispatch))
    graph.add_node("query_writer", make_query_writer(dispatch))
    graph.add_node("hunter", make_hunter(dispatch))
    graph.add_node("triage", make_triage(dispatch))
    graph.add_node("escalator", make_escalator(dispatch, escalation_threshold))

    graph.set_entry_point("hypothesis_planner")
    graph.add_conditional_edges(
        "hypothesis_planner",
        _route_after_planner,
        {"query_writer": "query_writer", "escalator": "escalator"},
    )
    graph.add_edge("query_writer", "hunter")
    graph.add_edge("hunter", "triage")
    graph.add_edge("triage", "escalator")
    graph.add_edge("escalator", END)

    return graph.compile()
