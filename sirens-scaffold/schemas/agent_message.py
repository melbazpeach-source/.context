"""Sirens agent-to-agent and agent-to-supervisor message schema.

Every hop on the LangGraph carries an `AgentMessage`. The supervisor uses the
`audit` block to enforce budgets, the `markings` block to enforce TLP, and the
`provenance` block to keep the knowledge graph free of laundered claims.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from schemas.tasking import TLP


SCHEMA_VERSION = "1.0.0"


class PayloadType(str, Enum):
    OBSERVABLE = "observable"            # raw IOC, file hash, domain, etc.
    HYPOTHESIS = "hypothesis"            # analyst proposes a link
    FINDING = "finding"                  # confirmed result
    REQUEST_ACTION = "request_action"    # agent asks supervisor to do X
    STATUS = "status"                    # heartbeat / progress
    REPORT = "report"                    # final structured artifact (STIX, MISP, etc.)
    ERROR = "error"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Provenance(BaseModel):
    source: str                          # e.g. "abuse.ch:malwarebazaar"
    collected_at: datetime
    fetched_via: str | None = None       # tool / API endpoint
    license: str | None = None           # ToS / data license tag
    raw_id: str | None = None            # source-side primary key, if any


class ToolCall(BaseModel):
    tool: str                            # MCP tool name
    started_at: datetime
    duration_ms: int = Field(ge=0)
    cost_usd: float = Field(default=0.0, ge=0)
    success: bool


class Audit(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0)
    tool_calls: list[ToolCall] = Field(default_factory=list)


class AgentMessage(BaseModel):
    """One message between agents on the LangGraph."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    message_id: UUID = Field(default_factory=uuid4)
    in_reply_to: UUID | None = None
    tasking_id: UUID

    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    from_agent: str                       # "research.collector.shodan"
    to_agent: str | None = None           # None == broadcast to swarm
    swarm: Literal["research", "hunt", "ir", "detection", "deception", "supervisor"]

    payload_type: PayloadType
    payload: dict[str, Any]               # JSON; STIX-shaped where possible
    confidence: Confidence = Confidence.MEDIUM

    markings: list[TLP] = Field(default_factory=lambda: [TLP.AMBER])
    provenance: list[Provenance] = Field(default_factory=list)
    audit: Audit = Field(default_factory=Audit)

    # HITL gate: if set to True, the supervisor must require human approval
    # before any downstream agent acts on this message.
    requires_human_approval: bool = False
