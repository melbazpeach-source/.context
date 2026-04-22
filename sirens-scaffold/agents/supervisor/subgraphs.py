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
    from agents.research import ResearchDispatch


SwarmRegistry = dict[str, Any]


def build_default_swarms(
    research_dispatch: "ResearchDispatch | None" = None,
) -> SwarmRegistry:
    """Build the default registry.

    Only the Research swarm is wired. Passing `research_dispatch=None` falls
    back to `StubDispatch` — the supervisor golden-path test runs in this mode.

    Imports are deferred to call-time: importing `agents.research` eagerly at
    module load would create a cycle via `agents.supervisor.middleware.audit`,
    which Research nodes depend on.
    """
    from agents.research import build_research_graph

    return {
        "research": build_research_graph(research_dispatch),
        # Phase 4+: add hunt / ir / detection / deception subgraphs here.
    }
