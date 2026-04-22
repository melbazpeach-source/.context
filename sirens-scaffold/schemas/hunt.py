"""Sirens Hunt-swarm schemas.

Carry the Hunt pipeline's typed artifacts:

    Tasking → Hypothesis (hypothesis-planner)
            → SigmaQuery (query-writer)
            → Hit (hunter: Wazuh / OpenSearch)
            → TriagedHit (triage-analyst: OpenCTI context)
            → HuntCase | None + HuntReport (escalator: TheHive)

The swarm reads telemetry via `mcp-server-wazuh`, applies pySigma rule
translation in-process, and opens cases via `mcp-server-thehive`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from schemas.tasking import TLP


SCHEMA_VERSION = "1.0.0"


class HypothesisKind(str, Enum):
    TTP_DETECTION = "ttp_detection"   # e.g. "detect T1566.001 phishing"
    IOC_SWEEP = "ioc_sweep"           # e.g. "hunt for this IP in logs"
    ANOMALY = "anomaly"               # e.g. "unusual parent→child process"
    RULE_GAP = "rule_gap"             # e.g. "hypothesise a rule that would have caught X"


class Triage(str, Enum):
    CONFIRMED = "confirmed"
    SUSPICIOUS = "suspicious"
    BENIGN = "benign"
    NEEDS_HUMAN = "needs_human"


class Hypothesis(BaseModel):
    """One hunt hypothesis the Query-Writer will convert to Sigma rules."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    hypothesis_id: UUID = Field(default_factory=uuid4)
    kind: HypothesisKind
    title: str
    ttp: str | None = None   # ATT&CK T-ID when applicable, e.g. "T1566.001"
    rationale: str | None = None
    tlp: TLP = TLP.AMBER


class SigmaQuery(BaseModel):
    """A translated Sigma rule ready to execute against a log backend."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    query_id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    sigma_rule_id: str | None = None   # upstream SigmaHQ rule id if sourced
    rule_yaml: str                      # the Sigma rule body
    backend: str                        # "opensearch-wazuh", "splunk", ...
    translated: str                     # backend-native query string
    index_patterns: list[str] = Field(default_factory=list)
    severity: int = Field(default=2, ge=1, le=4)


class Hit(BaseModel):
    """One log event matching a SigmaQuery. Pre-triage."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    hit_id: UUID = Field(default_factory=uuid4)
    query_id: UUID
    timestamp: datetime
    source: str                         # "wazuh-indexer:ecs-logs-*"
    host: str | None = None
    user: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    markings: list[TLP] = Field(default_factory=lambda: [TLP.AMBER])


class TriagedHit(BaseModel):
    """A Hit after correlation against OpenCTI context."""

    model_config = ConfigDict(extra="forbid")

    hit: Hit
    triage: Triage
    confidence: int = Field(default=50, ge=0, le=100)
    context: dict[str, Any] = Field(default_factory=dict)  # actor / campaign / malware anchors
    notes: str | None = None
    triaged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HuntCase(BaseModel):
    """Reference to a TheHive case opened by the Escalator."""

    model_config = ConfigDict(extra="forbid")

    case_id: str                         # TheHive case id
    case_url: str | None = None
    title: str
    severity: int = Field(default=2, ge=1, le=4)
    hit_ids: list[UUID] = Field(default_factory=list)
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HuntReport(BaseModel):
    """Final Hunt-swarm artifact."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    report_id: UUID = Field(default_factory=uuid4)
    tasking_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    hypotheses: list[Hypothesis] = Field(default_factory=list)
    queries: list[SigmaQuery] = Field(default_factory=list)
    hits: list[Hit] = Field(default_factory=list)
    triaged: list[TriagedHit] = Field(default_factory=list)
    case: HuntCase | None = None

    narrative: str
    tlp: TLP = TLP.AMBER
