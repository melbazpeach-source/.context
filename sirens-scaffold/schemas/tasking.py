"""Sirens supervisor tasking schema.

A `Tasking` is the only thing the supervisor accepts as a unit of work. It
encodes WHO is asking, WHAT to do, AGAINST WHICH targets (allow-list),
UNDER WHAT scope (markings, TLP, posture), WITHIN WHAT budget, and BY WHEN.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


SCHEMA_VERSION = "1.0.0"


class TaskingType(str, Enum):
    TRACK_ACTOR = "track_actor"
    WATCH_LEAK = "watch_leak"
    HUNT_TTP = "hunt_ttp"
    INGEST_REPORT = "ingest_report"
    ENRICH_OBSERVABLE = "enrich_observable"
    AUTHOR_DETECTION = "author_detection"
    INVESTIGATE_INCIDENT = "investigate_incident"
    DEPLOY_DECEPTION = "deploy_deception"


class Posture(str, Enum):
    PASSIVE_PUBLIC = "passive_public"
    DECEPTION_INTERNAL = "deception_internal"
    DECEPTION_AUTHORIZED = "deception_authorized"


class TLP(str, Enum):
    CLEAR = "TLP:CLEAR"
    GREEN = "TLP:GREEN"
    AMBER = "TLP:AMBER"
    AMBER_STRICT = "TLP:AMBER+STRICT"
    RED = "TLP:RED"


class TargetKind(str, Enum):
    DOMAIN = "domain"
    IP = "ip"
    ASN = "asn"
    URL = "url"
    FILE_HASH = "file_hash"
    EMAIL = "email"
    ACTOR = "actor"
    CAMPAIGN = "campaign"
    MALWARE_FAMILY = "malware_family"
    CVE = "cve"
    REPORT_URL = "report_url"


class Target(BaseModel):
    kind: TargetKind
    value: str = Field(..., min_length=1, max_length=512)
    notes: str | None = None


class Budget(BaseModel):
    max_input_tokens: int = Field(default=2_000_000, ge=0)
    max_output_tokens: int = Field(default=400_000, ge=0)
    max_cost_usd: float = Field(default=25.0, ge=0)
    deadline: datetime | None = None


class Authorization(BaseModel):
    """Anchored to the scope allow-list. Required for any non-passive posture."""
    allowlist_id: str
    approver: str
    approved_at: datetime
    expires_at: datetime
    reference: str | None = None  # ticket / contract / court order

    @field_validator("expires_at")
    @classmethod
    def _expiry_after_approval(cls, v: datetime, info) -> datetime:
        approved = info.data.get("approved_at")
        if approved and v <= approved:
            raise ValueError("expires_at must be after approved_at")
        return v


class Tasking(BaseModel):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    tasking_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requester: str = Field(..., min_length=1)

    type: TaskingType
    targets: Annotated[list[Target], Field(min_length=1, max_length=200)]
    posture: Posture = Posture.PASSIVE_PUBLIC

    tlp: TLP = TLP.AMBER
    budget: Budget = Field(default_factory=Budget)
    priority: int = Field(default=3, ge=1, le=5)

    authorization: Authorization | None = None
    references: list[HttpUrl] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("authorization")
    @classmethod
    def _authorization_required_for_active(cls, v, info):
        posture = info.data.get("posture")
        if posture in {Posture.DECEPTION_AUTHORIZED} and v is None:
            raise ValueError(
                "authorization is required when posture is DECEPTION_AUTHORIZED"
            )
        return v
