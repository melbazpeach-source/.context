"""Assemble the supervisor LangGraph.

    intake → (violations?) → finalize
           ↓
         plan → dispatch → finalize
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.supervisor.nodes import finalize, make_dispatch, make_intake, plan
from agents.supervisor.policy import ScopeAllowlist
from agents.supervisor.state import SupervisorState
from agents.supervisor.subgraphs import SwarmRegistry, build_default_swarms


def _route_after_intake(state: SupervisorState) -> str:
    if state.get("violations"):
        return "finalize"
    return "plan"


def build_supervisor_graph(
    allowlist: ScopeAllowlist,
    swarms: SwarmRegistry | None = None,
):
    """Return a compiled LangGraph app.

    `swarms` lets callers inject live-wired subgraphs (e.g. Research with a
    LiveDispatch). When `None`, falls back to `build_default_swarms()` which
    wires Research with `StubDispatch`.
    """
    if swarms is None:
        swarms = build_default_swarms()

    graph = StateGraph(SupervisorState)

    graph.add_node("intake", make_intake(allowlist))
    graph.add_node("plan", plan)
    graph.add_node("dispatch", make_dispatch(swarms))
    graph.add_node("finalize", finalize)

    graph.set_entry_point("intake")
    graph.add_conditional_edges(
        "intake",
        _route_after_intake,
        {"plan": "plan", "finalize": "finalize"},
    )
    graph.add_edge("plan", "dispatch")
    graph.add_edge("dispatch", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()
