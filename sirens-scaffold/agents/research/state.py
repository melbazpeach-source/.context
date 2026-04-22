"""LangGraph state for the Research swarm.

Mirrors SupervisorState: reducer channels for lists (`_append`), scalar fields
overwrite. Nodes return partial updates only.
"""

from __future__ import annotations

from typing import Annotated, TypedDict
from uuid import UUID

from schemas.agent_message import AgentMessage
from schemas.research import (
    Campaign,
    EnrichedObservable,
    Observable,
    ResearchQuery,
    ResearchReport,
)
from schemas.tasking import Tasking


def _append(left: list | None, right: list | None) -> list:
    """Channel reducer: concatenate, tolerate None on either side."""
    return [*(left or []), *(right or [])]


class ResearchState(TypedDict, total=False):
    """State carried through planner → collector → enricher → correlator → analyst → reporter."""

    tasking: Tasking
    run_id: UUID

    queries: Annotated[list[ResearchQuery], _append]
    observables: Annotated[list[Observable], _append]
    enriched: Annotated[list[EnrichedObservable], _append]

    campaign: Campaign | None
    narrative: str | None
    report: ResearchReport | None

    messages: Annotated[list[AgentMessage], _append]
    violations: Annotated[list[str], _append]

    current_step: str
    done: bool
