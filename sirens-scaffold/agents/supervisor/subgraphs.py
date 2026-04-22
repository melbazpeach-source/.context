"""Swarm registry — compiled subgraphs the supervisor dispatches into.

The supervisor's `dispatch` node looks up the next swarm in this registry.
Phase 3 kickoff wires `"research"`; `"hunt"`, `"ir"`, `"detection"`, and
`"deception"` stay `None` until those swarms exist, in which case dispatch
falls back to a STATUS-only message.

For live runs, callers build their own registry with `LiveDispatch`-backed
subgraphs and pass it to `build_supervisor_graph(allowlist, swarms=...)`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from agents.hunt import HuntDispatch
    from agents.research import ResearchDispatch


SwarmRegistry = dict[str, Any]


def build_default_swarms(
    research_dispatch: "ResearchDispatch | None" = None,
    hunt_dispatch: "HuntDispatch | None" = None,
) -> SwarmRegistry:
    """Build the default registry.

    Research and Hunt are wired. Passing `*_dispatch=None` falls back to each
    swarm's `StubDispatch` — the supervisor golden-path test runs in this mode.

    Imports are deferred to call-time: importing the swarms eagerly at module
    load would create a cycle via `agents.supervisor.middleware.audit`, which
    the swarm nodes depend on.
    """
    from agents.hunt import build_hunt_graph
    from agents.research import build_research_graph

    return {
        "research": build_research_graph(research_dispatch),
        "hunt": build_hunt_graph(hunt_dispatch),
        # Phase 5+: add ir / detection / deception subgraphs here.
    }
