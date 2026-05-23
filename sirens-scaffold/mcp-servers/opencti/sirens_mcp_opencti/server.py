"""Sirens MCP server for OpenCTI.

Surface (first cut):
    - search_entities       — full-text search across STIX entities
    - get_entity            — fetch by internal id
    - list_reports          — filter reports by tag / recency
    - create_indicator      — write an indicator (STIX pattern)
    - create_report         — write a report and link object_refs
    - add_relationship      — link two existing entities

Every tool requires `x-tasking-id`. Writes are tagged with the tasking id
so provenance survives through the knowledge graph.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import structlog
from mcp.server.fastmcp import Context, FastMCP
from pycti import OpenCTIApiClient
from pydantic import BaseModel, Field


log = structlog.get_logger("sirens.mcp.opencti")

OPENCTI_URL = os.environ.get("OPENCTI_URL", "http://opencti:8080")
OPENCTI_TOKEN = os.environ.get("OPENCTI_TOKEN", "")
OPENCTI_SSL_VERIFY = os.environ.get("OPENCTI_SSL_VERIFY", "true").lower() == "true"


mcp = FastMCP("sirens-opencti", dependencies=["pycti", "pydantic"])


_client: OpenCTIApiClient | None = None


def _api() -> OpenCTIApiClient:
    global _client
    if _client is None:
        if not OPENCTI_TOKEN:
            raise RuntimeError("OPENCTI_TOKEN not set")
        _client = OpenCTIApiClient(
            url=OPENCTI_URL,
            token=OPENCTI_TOKEN,
            ssl_verify=OPENCTI_SSL_VERIFY,
            log_level="info",
        )
    return _client


def _require_tasking(ctx: Context) -> str:
    headers = getattr(ctx, "request_headers", {}) or {}
    tid = headers.get("x-tasking-id") or headers.get("X-Tasking-Id")
    if not tid:
        raise ValueError("x-tasking-id header required — supervisor must set it")
    return tid


def _tasking_label(tid: str) -> str:
    return f"sirens:tasking:{tid}"


# ---------- Schemas ----------


class EntitySummary(BaseModel):
    id: str
    standard_id: str | None = None
    entity_type: str
    name: str | None = None
    description: str | None = None
    created: str | None = None
    modified: str | None = None
    confidence: int | None = None


class Report(BaseModel):
    id: str
    standard_id: str | None = None
    name: str
    published: str | None = None
    report_types: list[str] = Field(default_factory=list)
    confidence: int | None = None


class CreateIndicatorInput(BaseModel):
    pattern: str = Field(..., description="STIX pattern, e.g. [ipv4-addr:value = '1.2.3.4']")
    pattern_type: str = "stix"
    name: str
    description: str | None = None
    indicator_types: list[str] = Field(default_factory=lambda: ["malicious-activity"])
    confidence: int = Field(50, ge=0, le=100)
    valid_from: str | None = None
    x_opencti_score: int = Field(50, ge=0, le=100)


class CreateReportInput(BaseModel):
    name: str
    published: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    description: str | None = None
    content: str | None = None
    report_types: list[str] = Field(default_factory=lambda: ["threat-report"])
    confidence: int = Field(50, ge=0, le=100)
    object_refs: list[str] = Field(default_factory=list)


class RelationshipInput(BaseModel):
    from_id: str
    to_id: str
    relationship_type: str = Field(..., description="e.g. indicates, uses, attributed-to")
    description: str | None = None
    confidence: int = Field(50, ge=0, le=100)
    start_time: str | None = None
    stop_time: str | None = None


# ---------- Tools ----------


@mcp.tool()
def search_entities(
    ctx: Context,
    query: str,
    entity_types: list[str] | None = None,
    limit: int = 25,
) -> list[EntitySummary]:
    """Full-text search across STIX entities (domain objects + observables)."""
    _require_tasking(ctx)
    api = _api()
    filters: dict[str, Any] | None = None
    if entity_types:
        filters = {
            "mode": "and",
            "filters": [{"key": "entity_type", "values": entity_types}],
            "filterGroups": [],
        }
    rows = api.stix_core_object.list(
        search=query,
        filters=filters,
        first=max(1, min(limit, 200)),
    )
    return [_to_summary(r) for r in rows]


@mcp.tool()
def get_entity(ctx: Context, entity_id: str) -> EntitySummary | None:
    """Fetch a single STIX entity by OpenCTI internal id or standard_id."""
    _require_tasking(ctx)
    api = _api()
    row = api.stix_core_object.read(id=entity_id)
    return _to_summary(row) if row else None


@mcp.tool()
def list_reports(
    ctx: Context,
    search: str | None = None,
    limit: int = 25,
) -> list[Report]:
    """List reports, optionally filtered by free-text search."""
    _require_tasking(ctx)
    api = _api()
    rows = api.report.list(search=search, first=max(1, min(limit, 200)))
    return [
        Report(
            id=r["id"],
            standard_id=r.get("standard_id"),
            name=r.get("name", ""),
            published=r.get("published"),
            report_types=r.get("report_types") or [],
            confidence=r.get("confidence"),
        )
        for r in rows
    ]


@mcp.tool()
def create_indicator(ctx: Context, payload: CreateIndicatorInput) -> EntitySummary:
    """Create an Indicator. Tagged with the caller's tasking id."""
    tid = _require_tasking(ctx)
    api = _api()
    result = api.indicator.create(
        pattern=payload.pattern,
        pattern_type=payload.pattern_type,
        name=payload.name,
        description=payload.description,
        indicator_types=payload.indicator_types,
        confidence=payload.confidence,
        valid_from=payload.valid_from,
        x_opencti_score=payload.x_opencti_score,
        update=True,
    )
    _tag(api, result["id"], tid)
    return _to_summary(result)


@mcp.tool()
def create_report(ctx: Context, payload: CreateReportInput) -> Report:
    """Create a Report and link `object_refs` (entity ids already in OpenCTI)."""
    tid = _require_tasking(ctx)
    api = _api()
    result = api.report.create(
        name=payload.name,
        published=payload.published,
        description=payload.description,
        content=payload.content,
        report_types=payload.report_types,
        confidence=payload.confidence,
        objects=payload.object_refs,
        update=True,
    )
    _tag(api, result["id"], tid)
    return Report(
        id=result["id"],
        standard_id=result.get("standard_id"),
        name=result.get("name", payload.name),
        published=result.get("published", payload.published),
        report_types=result.get("report_types") or payload.report_types,
        confidence=result.get("confidence", payload.confidence),
    )


@mcp.tool()
def add_relationship(ctx: Context, payload: RelationshipInput) -> dict[str, str]:
    """Create a STIX Core Relationship between two existing entities."""
    tid = _require_tasking(ctx)
    api = _api()
    rel = api.stix_core_relationship.create(
        fromId=payload.from_id,
        toId=payload.to_id,
        relationship_type=payload.relationship_type,
        description=payload.description,
        confidence=payload.confidence,
        start_time=payload.start_time,
        stop_time=payload.stop_time,
        update=True,
    )
    _tag(api, rel["id"], tid)
    return {"id": rel["id"], "standard_id": rel.get("standard_id", "")}


# ---------- Helpers ----------


def _to_summary(row: dict[str, Any] | None) -> EntitySummary:
    if not row:
        raise ValueError("empty row")
    return EntitySummary(
        id=row["id"],
        standard_id=row.get("standard_id"),
        entity_type=row.get("entity_type", "Unknown"),
        name=row.get("name") or row.get("value") or row.get("observable_value"),
        description=row.get("description"),
        created=row.get("created"),
        modified=row.get("modified"),
        confidence=row.get("confidence"),
    )


def _tag(api: OpenCTIApiClient, entity_id: str, tasking_id: str) -> None:
    """Attach a tasking label to a newly-created entity. Best-effort."""
    try:
        label_value = _tasking_label(tasking_id)
        label = api.label.read(filters={
            "mode": "and",
            "filters": [{"key": "value", "values": [label_value]}],
            "filterGroups": [],
        })
        if not label:
            label = api.label.create(value=label_value, color="#FF6B35")
        api.stix_core_object.add_label(id=entity_id, label_id=label["id"])
    except Exception as exc:  # noqa: BLE001 — tagging is best-effort
        log.warning("tag_failed", entity_id=entity_id, error=str(exc))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
