"""LangGraph state for the Hunt swarm.

Mirrors ResearchState / SupervisorState: reducer-channel lists via `_append`,
scalar fields overwrite. Nodes return partial updates only.
"""

from __future__ import annotations

from typing import Annotated, TypedDict
from uuid import UUID

from schemas.agent_message import AgentMessage
from schemas.hunt import (
    Hit,
    HuntCase,
    HuntReport,
    Hypothesis,
    SigmaQuery,
    TriagedHit,
)
from schemas.tasking import Tasking


def _append(left: list | None, right: list | None) -> list:
    """Channel reducer: concatenate, tolerate None on either side."""
    return [*(left or []), *(right or [])]


class HuntState(TypedDict, total=False):
    """Carried through hypothesis_planner → query_writer → hunter → triage → escalator."""

    tasking: Tasking
    run_id: UUID

    hypotheses: Annotated[list[Hypothesis], _append]
    queries: Annotated[list[SigmaQuery], _append]
    hits: Annotated[list[Hit], _append]
    triaged: Annotated[list[TriagedHit], _append]

    case: HuntCase | None
    narrative: str | None
    report: HuntReport | None

    messages: Annotated[list[AgentMessage], _append]
    violations: Annotated[list[str], _append]

    current_step: str
    done: bool
