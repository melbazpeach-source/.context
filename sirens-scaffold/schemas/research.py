"""Sirens Research-swarm schemas.

Carry the Research pipeline's typed artifacts:

    Tasking → ResearchQuery (planner)
            → Observable (collector)
            → EnrichedObservable (enricher: IntelOwl)
            → Campaign (correlator: OpenCTI pivot)
            → DraftDetection + narrative (analyst)
            → ResearchReport (reporter: STIX + MISP + TheHive)

Everything persists to the knowledge spine via MCP brokers; these classes are
the in-flight shape between LangGraph nodes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from schemas.agent_message import Provenance
from schemas.tasking import TLP, Target


SCHEMA_VERSION = "1.0.0"


class QueryKind(str, Enum):
    INFRA = "infra"                # shodan, censys, greynoise, fofa
    MALWARE = "malware"            # abuse.ch, virustotal, hybrid-analysis
    PASSIVE_DNS = "passive_dns"    # dnsdb, domaintools, mnemonic
    TI_PLATFORM = "ti_platform"    # otx, misp feeds, opencti connectors
    LEAK = "leak"                  # gitguardian, gist/dork, pastebin mirrors
    SOCIAL = "social"              # x, mastodon, telegram public, reddit
    DARK_WEB = "dark_web"          # ahmia, deepdarkCTI
    CVE = "cve"                    # nvd, kev, vulncheck, pocingithub
    DECEPTION = "deception"        # canarytokens, opencanary, mhn callbacks


class ObservableKind(str, Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    FILE_HASH = "file_hash"
    EMAIL = "email"
    ACTOR_ALIAS = "actor_alias"
    MALWARE_FAMILY = "malware_family"
    BOTNET_C2 = "botnet_c2"
    YARA_HIT = "yara_hit"
    CVE = "cve"


class DetectionKind(str, Enum):
    SIGMA = "sigma"
    YARA = "yara"
    NUCLEI = "nuclei"


class Verdict(str, Enum):
    MALICIOUS = "malicious"
    SUSPICIOUS = "suspicious"
    CLEAN = "clean"
    UNKNOWN = "unknown"


class ResearchQuery(BaseModel):
    """One unit of work handed from Planner → Collector.

    A tasking with 3 targets and 4 query kinds produces up to 12 queries.
    Each query names the concrete source list the Collector will fan-out to.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    query_id: UUID = Field(default_factory=uuid4)
    kind: QueryKind
    target: Target
    sources: list[str] = Field(default_factory=list, min_length=0)
    tlp: TLP = TLP.AMBER
    rationale: str | None = None


class Observable(BaseModel):
    """Pre-enrichment collector output. One per atomic indicator."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    observable_id: UUID = Field(default_factory=uuid4)
    kind: ObservableKind
    value: str = Field(..., min_length=1, max_length=4096)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    query_id: UUID | None = None
    provenance: Provenance
    markings: list[TLP] = Field(default_factory=lambda: [TLP.AMBER])
    raw: dict[str, Any] = Field(default_factory=dict)


class EnrichedObservable(BaseModel):
    """Collector Observable + IntelOwl analyzer fan-out."""

    model_config = ConfigDict(extra="forbid")

    observable: Observable
    analyzers: dict[str, Any] = Field(default_factory=dict)
    verdict: Verdict = Verdict.UNKNOWN
    tags: list[str] = Field(default_factory=list)
    enriched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CampaignEdge(BaseModel):
    """STIX-SRO-shaped relationship between two campaign entities."""

    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    target_id: UUID
    relationship_type: str   # "indicates" / "communicates-with" / "attributed-to"
    confidence: int = Field(default=50, ge=0, le=100)


class Campaign(BaseModel):
    """Correlator output — actor/infra graph derived from enriched observables."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    campaign_id: UUID = Field(default_factory=uuid4)
    name: str | None = None
    actor_aliases: list[str] = Field(default_factory=list)
    ttps: list[str] = Field(default_factory=list)  # ATT&CK T-IDs (e.g. "T1566.001")
    observable_ids: list[UUID] = Field(default_factory=list)
    edges: list[CampaignEdge] = Field(default_factory=list)
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class DraftDetection(BaseModel):
    """A Sigma / YARA / Nuclei rule draft produced by the Analyst.

    Rules are drafts until the Detection-Engineering swarm tests + tunes them.
    """

    model_config = ConfigDict(extra="forbid")

    kind: DetectionKind
    title: str
    content: str                # rule YAML / YARA source / nuclei template
    ttps: list[str] = Field(default_factory=list)
    confidence: int = Field(default=50, ge=0, le=100)


class ResearchReport(BaseModel):
    """Final artifact from the Research swarm. Reporter writes one per run."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    report_id: UUID = Field(default_factory=uuid4)
    tasking_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    narrative: str
    campaign: Campaign | None = None
    enriched: list[EnrichedObservable] = Field(default_factory=list)
    draft_detections: list[DraftDetection] = Field(default_factory=list)

    stix_bundle: dict[str, Any] = Field(default_factory=dict)
    misp_event_json: dict[str, Any] | None = None
    thehive_case_ref: str | None = None

    tlp: TLP = TLP.AMBER
