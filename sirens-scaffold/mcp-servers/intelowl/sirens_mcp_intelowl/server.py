"""Sirens MCP server for IntelOwl.

Exposes a small surface of IntelOwl REST endpoints as MCP tools:
    - submit_observable
    - get_job
    - list_analyzers
    - list_playbooks

Every tool call requires an `x-tasking-id` header; the server refuses
untagged calls so the supervisor's audit trail stays whole.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field


log = structlog.get_logger("sirens.mcp.intelowl")

INTELOWL_URL = os.environ.get("INTELOWL_URL", "http://intelowl:80")
INTELOWL_TOKEN = os.environ.get("INTELOWL_TOKEN", "")
DEFAULT_TIMEOUT = float(os.environ.get("INTELOWL_TIMEOUT", "30"))


mcp = FastMCP("sirens-intelowl", dependencies=["httpx", "pydantic"])


def _client() -> httpx.AsyncClient:
    if not INTELOWL_TOKEN:
        raise RuntimeError("INTELOWL_TOKEN not set")
    return httpx.AsyncClient(
        base_url=INTELOWL_URL,
        timeout=DEFAULT_TIMEOUT,
        headers={
            "Authorization": f"Token {INTELOWL_TOKEN}",
            "User-Agent": "sirens-mcp-intelowl/0.1",
        },
    )


def _require_tasking(ctx: Context) -> str:
    """Refuse calls that arrived without a tasking_id."""
    headers = getattr(ctx, "request_headers", {}) or {}
    tid = headers.get("x-tasking-id") or headers.get("X-Tasking-Id")
    if not tid:
        raise ValueError("x-tasking-id header required — supervisor must set it")
    return tid


# ---------- Schemas ----------


class Observable(BaseModel):
    value: str = Field(..., min_length=1, max_length=2048)
    classification: str = Field(..., description="ip|domain|url|hash|generic")
    tlp: str = Field("AMBER", description="CLEAR|GREEN|AMBER|RED")


class SubmitResponse(BaseModel):
    job_id: int
    status: str


class JobStatus(BaseModel):
    job_id: int
    status: str
    analyzers_requested: list[str]
    analyzers_completed: list[str]
    verdict: str | None = None
    observable: str
    tags: list[str] = Field(default_factory=list)
    runtime_configuration: dict[str, Any] = Field(default_factory=dict)


# ---------- Tools ----------


@mcp.tool()
async def submit_observable(
    ctx: Context,
    observable: Observable,
    analyzers: list[str] | None = None,
    playbook: str | None = None,
) -> SubmitResponse:
    """Submit an observable to IntelOwl for analysis."""
    _require_tasking(ctx)
    body: dict[str, Any] = {
        "observables": [[observable.classification, observable.value]],
        "tlp": observable.tlp,
    }
    if playbook:
        body["playbook_requested"] = playbook
    elif analyzers:
        body["analyzers_requested"] = analyzers
    async with _client() as http:
        r = await http.post("/api/analyze_multiple_observables", json=body)
        r.raise_for_status()
        data = r.json()
    job_id = data["results"][0]["job_id"]
    return SubmitResponse(job_id=int(job_id), status=data["results"][0].get("status", "pending"))


@mcp.tool()
async def get_job(ctx: Context, job_id: int) -> JobStatus:
    """Fetch current status and findings for a job."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get(f"/api/jobs/{job_id}")
        r.raise_for_status()
        d = r.json()
    return JobStatus(
        job_id=int(d["id"]),
        status=d["status"],
        analyzers_requested=d.get("analyzers_requested", []),
        analyzers_completed=d.get("analyzers_to_execute", []),
        verdict=d.get("verdict"),
        observable=d.get("observable_name", ""),
        tags=[t.get("label", "") for t in d.get("tags", [])],
        runtime_configuration=d.get("runtime_configuration", {}),
    )


@mcp.tool()
async def list_analyzers(ctx: Context) -> list[str]:
    """Enumerate analyzers IntelOwl knows about."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get("/api/analyzer")
        r.raise_for_status()
        return sorted(r.json().keys())


@mcp.tool()
async def list_playbooks(ctx: Context) -> list[str]:
    """Enumerate playbooks IntelOwl knows about."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get("/api/playbook")
        r.raise_for_status()
        return sorted(r.json().keys())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
