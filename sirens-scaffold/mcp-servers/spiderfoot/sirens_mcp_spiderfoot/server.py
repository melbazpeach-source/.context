"""Sirens MCP server for SpiderFoot (OSS).

Surface:
    - start_scan           — kick off a scan (Passive by default)
    - get_scan             — status for a scan id
    - list_scans           — enumerate scans, optionally filtered
    - get_scan_results     — findings for a scan id
    - get_scan_summary     — aggregated counts per event type
    - list_modules         — modules SpiderFoot has loaded
    - list_event_types     — event types SpiderFoot can emit
    - stop_scan            — abort a running scan

Ethical default: scans run with `usecase=Passive`. Non-passive usecases
(`Footprint`, `Investigate`, `all`) require an explicit `x-active-authorization`
header set by the supervisor from the tasking's Authorization record.
This enforces the posture policy at the tool boundary.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

import httpx
import structlog
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field


log = structlog.get_logger("sirens.mcp.spiderfoot")

SPIDERFOOT_URL = os.environ.get("SPIDERFOOT_URL", "http://spiderfoot:5001")
SPIDERFOOT_USER = os.environ.get("SPIDERFOOT_USER", "")
SPIDERFOOT_PASSWORD = os.environ.get("SPIDERFOOT_PASSWORD", "")
DEFAULT_TIMEOUT = float(os.environ.get("SPIDERFOOT_TIMEOUT", "60"))


mcp = FastMCP("sirens-spiderfoot", dependencies=["httpx", "pydantic"])


class UseCase(str, Enum):
    PASSIVE = "Passive"
    FOOTPRINT = "Footprint"
    INVESTIGATE = "Investigate"
    ALL = "all"


def _auth() -> httpx.BasicAuth | None:
    if SPIDERFOOT_USER and SPIDERFOOT_PASSWORD:
        return httpx.BasicAuth(SPIDERFOOT_USER, SPIDERFOOT_PASSWORD)
    return None


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=SPIDERFOOT_URL,
        timeout=DEFAULT_TIMEOUT,
        auth=_auth(),
        headers={
            "Accept": "application/json",
            "User-Agent": "sirens-mcp-spiderfoot/0.1",
        },
    )


def _require_tasking(ctx: Context) -> str:
    headers = getattr(ctx, "request_headers", {}) or {}
    tid = headers.get("x-tasking-id") or headers.get("X-Tasking-Id")
    if not tid:
        raise ValueError("x-tasking-id header required — supervisor must set it")
    return tid


def _active_authorized(ctx: Context) -> bool:
    headers = getattr(ctx, "request_headers", {}) or {}
    return str(headers.get("x-active-authorization", "")).lower() in {"1", "true", "yes"}


# ---------- Schemas ----------


class Scan(BaseModel):
    id: str
    name: str
    target: str
    status: str
    created: str | None = None
    started: str | None = None
    ended: str | None = None
    total_elements: int | None = None


class ScanResult(BaseModel):
    generated: str | None = None
    event_type: str
    data: str
    source: str | None = None
    module: str | None = None
    confidence: int | None = None
    risk: str | None = None


class ScanSummary(BaseModel):
    event_type: str
    count: int
    last_seen: str | None = None


class Module(BaseModel):
    name: str
    description: str | None = None
    categories: list[str] = Field(default_factory=list)


# ---------- Tools ----------


@mcp.tool()
async def list_modules(ctx: Context) -> list[Module]:
    """Enumerate modules SpiderFoot has loaded."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get("/modules")
        r.raise_for_status()
        rows = r.json()
    return [
        Module(
            name=row.get("name", ""),
            description=row.get("descr"),
            categories=row.get("cats") or [],
        )
        for row in rows
    ]


@mcp.tool()
async def list_event_types(ctx: Context) -> list[str]:
    """Enumerate event types SpiderFoot can emit."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get("/eventtypes")
        r.raise_for_status()
        rows = r.json()
    return sorted({row[0] for row in rows if row})


@mcp.tool()
async def start_scan(
    ctx: Context,
    target: str,
    name: str,
    usecase: UseCase = UseCase.PASSIVE,
    modules: list[str] | None = None,
    event_types: list[str] | None = None,
) -> Scan:
    """Start a scan. Refuses non-Passive usecase without x-active-authorization."""
    _require_tasking(ctx)
    if usecase is not UseCase.PASSIVE and not _active_authorized(ctx):
        raise PermissionError(
            f"usecase={usecase.value!r} requires x-active-authorization header "
            "(supervisor sets this from tasking.authorization)"
        )
    params: dict[str, Any] = {
        "scanname": name,
        "scantarget": target,
        "usecase": usecase.value,
        "modulelist": ",".join(modules) if modules else "",
        "typelist": ",".join(event_types) if event_types else "",
    }
    async with _client() as http:
        r = await http.get("/startscan", params=params)
        r.raise_for_status()
        data = r.json()
    # SpiderFoot returns ["SUCCESS", scan_id] on success or ["ERROR", msg].
    if not isinstance(data, list) or data[0] != "SUCCESS":
        raise RuntimeError(f"startscan failed: {data}")
    scan_id = data[1]
    return await get_scan(ctx, scan_id)


@mcp.tool()
async def get_scan(ctx: Context, scan_id: str) -> Scan:
    """Fetch scan status and metadata."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get("/scanopts", params={"id": scan_id})
        r.raise_for_status()
        data = r.json()
    meta = data.get("meta") or {}
    return Scan(
        id=scan_id,
        name=meta.get("name", ""),
        target=meta.get("target", ""),
        status=meta.get("status", "UNKNOWN"),
        created=meta.get("created"),
        started=meta.get("started"),
        ended=meta.get("ended"),
    )


@mcp.tool()
async def list_scans(
    ctx: Context,
    status_filter: str | None = None,
    limit: int = 25,
) -> list[Scan]:
    """List scans, optionally filtered by status (e.g. RUNNING, FINISHED, ABORTED)."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get("/scanlist")
        r.raise_for_status()
        rows = r.json()
    scans = [
        Scan(
            id=row[0],
            name=row[1],
            target=row[2],
            created=row[3],
            started=row[4],
            ended=row[5],
            status=row[6],
            total_elements=int(row[7]) if len(row) > 7 and row[7] is not None else None,
        )
        for row in rows
    ]
    if status_filter:
        scans = [s for s in scans if s.status == status_filter]
    return scans[: max(1, min(limit, 500))]


@mcp.tool()
async def get_scan_results(
    ctx: Context,
    scan_id: str,
    event_type: str | None = None,
    limit: int = 100,
) -> list[ScanResult]:
    """Fetch findings for a scan, optionally filtered by event type."""
    _require_tasking(ctx)
    params = {"id": scan_id, "eventType": event_type or "ALL"}
    async with _client() as http:
        r = await http.get("/scaneventresults", params=params)
        r.raise_for_status()
        rows = r.json()
    results = [
        ScanResult(
            generated=row[0] if len(row) > 0 else None,
            data=row[1] if len(row) > 1 else "",
            source=row[2] if len(row) > 2 else None,
            module=row[3] if len(row) > 3 else None,
            event_type=row[4] if len(row) > 4 else "UNKNOWN",
            confidence=int(row[6]) if len(row) > 6 and row[6] is not None else None,
            risk=row[8] if len(row) > 8 else None,
        )
        for row in rows
    ]
    return results[: max(1, min(limit, 5000))]


@mcp.tool()
async def get_scan_summary(ctx: Context, scan_id: str) -> list[ScanSummary]:
    """Aggregated counts per event type for a scan."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get("/scansummary", params={"id": scan_id, "by": "type"})
        r.raise_for_status()
        rows = r.json()
    return [
        ScanSummary(
            event_type=row[0],
            count=int(row[3]) if len(row) > 3 else 0,
            last_seen=row[2] if len(row) > 2 else None,
        )
        for row in rows
    ]


@mcp.tool()
async def stop_scan(ctx: Context, scan_id: str) -> dict[str, str]:
    """Abort a running scan."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get("/stopscan", params={"id": scan_id})
        r.raise_for_status()
    return {"id": scan_id, "status": "STOP_REQUESTED"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
