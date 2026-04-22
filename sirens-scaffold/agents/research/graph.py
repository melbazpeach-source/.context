"""Assemble the Research-swarm LangGraph.

    planner → (queries?) → reporter-empty
            ↓
          collector → enricher → correlator → analyst → reporter
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.research.dispatch import ResearchDispatch, StubDispatch
from agents.research.nodes import (
    make_analyst,
    make_collector,
    make_correlator,
    make_enricher,
    make_planner,
    make_reporter,
)
from agents.research.state import ResearchState


def _route_after_planner(state: ResearchState) -> str:
    """If the planner produced zero queries, skip straight to reporter.

    A zero-query state means the planner couldn't match any QueryKind to the
    tasking's targets — valid for a tasking-shape problem, but pointless to
    fan collectors out for nothing. Reporter still emits a report (empty one)
    so the caller always gets a typed result.
    """
    if not state.get("queries"):
        return "reporter"
    return "collector"


def build_research_graph(dispatch: ResearchDispatch | None = None):
    """Return a compiled LangGraph app for the Research swarm.

    Pass a `LiveDispatch` (Phase 3.1) for real MCP wiring, or leave as None to
    use `StubDispatch` — useful for unit tests and demos without the stack.
    """
    dispatch = dispatch or StubDispatch()
    graph = StateGraph(ResearchState)

    graph.add_node("planner", make_planner())
    graph.add_node("collector", make_collector(dispatch))
    graph.add_node("enricher", make_enricher(dispatch))
    graph.add_node("correlator", make_correlator(dispatch))
    graph.add_node("analyst", make_analyst(dispatch))
    graph.add_node("reporter", make_reporter(dispatch))

    graph.set_entry_point("planner")
    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {"collector": "collector", "reporter": "reporter"},
    )
    graph.add_edge("collector", "enricher")
    graph.add_edge("enricher", "correlator")
    graph.add_edge("correlator", "analyst")
    graph.add_edge("analyst", "reporter")
    graph.add_edge("reporter", END)

    return graph.compile()
