"""LangGraph state for the supervisor."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, TypedDict
from uuid import UUID

from schemas.agent_message import AgentMessage
from schemas.tasking import Tasking


def _append(left: list | None, right: list | None) -> list:
    """Channel reducer: concatenate, tolerate None on either side."""
    return [*(left or []), *(right or [])]


class BudgetLedger(TypedDict):
    input_tokens: int
    output_tokens: int
    cost_usd: float
    tool_calls: int
    started_at: datetime


class Violation(TypedDict):
    kind: str          # "budget" | "rate_limit" | "scope" | "ethics"
    detail: str
    raised_at: datetime


class SupervisorState(TypedDict, total=False):
    """The only thing that flows between supervisor nodes."""

    tasking: Tasking
    messages: Annotated[list[AgentMessage], _append]
    ledger: BudgetLedger
    violations: Annotated[list[Violation], _append]

    current_step: str
    next_swarm: str | None
    done: bool

    # Correlation
    run_id: UUID


def new_ledger() -> BudgetLedger:
    return BudgetLedger(
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        tool_calls=0,
        started_at=datetime.now(timezone.utc),
    )
