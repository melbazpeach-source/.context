"""Sirens MCP server for Velociraptor.

Surface:
    - list_clients         — enumerate / search enrolled clients
    - get_client           — single-client metadata
    - list_artifacts       — enumerate artifact definitions
    - collect_artifact     — kick off a named collection on a client
    - list_flows           — recent flows for a client
    - get_flow             — flow status
    - get_flow_results     — rows emitted by a flow's artifact
    - run_vql              — arbitrary VQL (active-authorization gated)

Authorization model: Velociraptor only touches endpoints we own
(customer-operated). All tools require `x-tasking-id`. `run_vql` — which
can do anything VQL can express — additionally requires
`x-active-authorization: true`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import grpc
import structlog
import yaml
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field
from pyvelociraptor import api_pb2, api_pb2_grpc


log = structlog.get_logger("sirens.mcp.velociraptor")

VELOCIRAPTOR_CONFIG = os.environ.get(
    "VELOCIRAPTOR_CONFIG", "/etc/velociraptor/api.config.yaml"
)
VELOCIRAPTOR_TIMEOUT = float(os.environ.get("VELOCIRAPTOR_TIMEOUT", "120"))


mcp = FastMCP("sirens-velociraptor", dependencies=["pyvelociraptor", "grpcio", "pyyaml"])


_stub: api_pb2_grpc.APIStub | None = None


def _stub_singleton() -> api_pb2_grpc.APIStub:
    global _stub
    if _stub is None:
        config = yaml.safe_load(Path(VELOCIRAPTOR_CONFIG).read_text())
        creds = grpc.ssl_channel_credentials(
            root_certificates=config["ca_certificate"].encode(),
            private_key=config["client_private_key"].encode(),
            certificate_chain=config["client_cert"].encode(),
        )
        options = (("grpc.ssl_target_name_override", "VelociraptorServer"),)
        channel = grpc.secure_channel(
            config["api_connection_string"], creds, options
        )
        _stub = api_pb2_grpc.APIStub(channel)
    return _stub


def _require_tasking(ctx: Context) -> str:
    headers = getattr(ctx, "request_headers", {}) or {}
    tid = headers.get("x-tasking-id") or headers.get("X-Tasking-Id")
    if not tid:
        raise ValueError("x-tasking-id header required — supervisor must set it")
    return tid


def _active_authorized(ctx: Context) -> bool:
    headers = getattr(ctx, "request_headers", {}) or {}
    return str(headers.get("x-active-authorization", "")).lower() in {"1", "true", "yes"}


def _vql(query: str, env: dict[str, str] | None = None) -> list[dict[str, Any]]:
    stub = _stub_singleton()
    request = api_pb2.VQLCollectorArgs(
        Query=[api_pb2.VQLRequest(VQL=query)],
        env=[api_pb2.VQLEnv(key=k, value=v) for k, v in (env or {}).items()],
        max_wait=int(VELOCIRAPTOR_TIMEOUT),
    )
    rows: list[dict[str, Any]] = []
    for response in stub.Query(request, timeout=VELOCIRAPTOR_TIMEOUT):
        if response.Response:
            chunk = json.loads(response.Response)
            if isinstance(chunk, list):
                rows.extend(chunk)
            else:
                rows.append(chunk)
    return rows


# ---------- Schemas ----------


class Client(BaseModel):
    client_id: str
    hostname: str | None = None
    os: str | None = None
    platform: str | None = None
    last_seen_at: int | None = None
    first_seen_at: int | None = None
    labels: list[str] = Field(default_factory=list)


class Artifact(BaseModel):
    name: str
    description: str | None = None
    type: str | None = None
    author: str | None = None


class Flow(BaseModel):
    flow_id: str
    client_id: str
    state: str
    artifacts: list[str] = Field(default_factory=list)
    create_time: int | None = None
    active_time: int | None = None
    total_collected_rows: int | None = None


# ---------- Tools ----------


@mcp.tool()
def list_clients(
    ctx: Context,
    search: str = "all",
    limit: int = 50,
) -> list[Client]:
    """Enumerate enrolled clients. `search` is a Velociraptor search expression."""
    _require_tasking(ctx)
    rows = _vql(
        "SELECT client_id, os_info.hostname AS hostname, "
        "os_info.system AS os, os_info.platform AS platform, "
        "last_seen_at, first_seen_at, labels "
        "FROM clients(search=search) LIMIT limit",
        env={"search": search, "limit": str(max(1, min(limit, 5000)))},
    )
    return [Client(**row) for row in rows]


@mcp.tool()
def get_client(ctx: Context, client_id: str) -> Client | None:
    """Fetch metadata for a single client."""
    _require_tasking(ctx)
    rows = _vql(
        "SELECT client_id, os_info.hostname AS hostname, "
        "os_info.system AS os, os_info.platform AS platform, "
        "last_seen_at, first_seen_at, labels "
        "FROM client_info(client_id=client_id)",
        env={"client_id": client_id},
    )
    return Client(**rows[0]) if rows else None


@mcp.tool()
def list_artifacts(
    ctx: Context,
    search: str = ".",
    limit: int = 100,
) -> list[Artifact]:
    """Enumerate artifact definitions. `search` is a regex on name."""
    _require_tasking(ctx)
    rows = _vql(
        "SELECT name, description, type, author FROM artifact_definitions() "
        "WHERE name =~ search LIMIT limit",
        env={"search": search, "limit": str(max(1, min(limit, 5000)))},
    )
    return [Artifact(**row) for row in rows]


@mcp.tool()
def collect_artifact(
    ctx: Context,
    client_id: str,
    artifact: str,
    parameters: dict[str, str] | None = None,
    ttl_seconds: int = 600,
) -> Flow:
    """Start a collection. Returns the new flow (initial state)."""
    _require_tasking(ctx)
    params = parameters or {}
    spec = {
        "artifacts": [artifact],
        "parameters": {"env": [{"key": k, "value": v} for k, v in params.items()]},
        "timeout": ttl_seconds,
    }
    rows = _vql(
        "SELECT collect_client(client_id=client_id, artifacts=artifacts, env=env) AS flow "
        "FROM scope()",
        env={
            "client_id": client_id,
            "artifacts": json.dumps([artifact]),
            "env": json.dumps(params),
        },
    )
    if not rows:
        raise RuntimeError(f"collect_client returned no rows for spec={spec}")
    flow = rows[0]["flow"]
    return Flow(
        flow_id=flow["flow_id"],
        client_id=client_id,
        state=flow.get("state", "UNKNOWN"),
        artifacts=[artifact],
        create_time=flow.get("create_time"),
    )


@mcp.tool()
def list_flows(
    ctx: Context,
    client_id: str,
    limit: int = 25,
) -> list[Flow]:
    """Recent flows for a client, newest first."""
    _require_tasking(ctx)
    rows = _vql(
        "SELECT session_id AS flow_id, client_id, state, "
        "artifacts_with_results AS artifacts, create_time, active_time, "
        "total_collected_rows "
        "FROM flows(client_id=client_id) ORDER BY create_time DESC LIMIT limit",
        env={"client_id": client_id, "limit": str(max(1, min(limit, 500)))},
    )
    return [Flow(**row) for row in rows]


@mcp.tool()
def get_flow(ctx: Context, client_id: str, flow_id: str) -> Flow | None:
    """Status and metadata for a specific flow."""
    _require_tasking(ctx)
    rows = _vql(
        "SELECT session_id AS flow_id, client_id, state, "
        "artifacts_with_results AS artifacts, create_time, active_time, "
        "total_collected_rows "
        "FROM flows(client_id=client_id, flow_id=flow_id)",
        env={"client_id": client_id, "flow_id": flow_id},
    )
    return Flow(**rows[0]) if rows else None


@mcp.tool()
def get_flow_results(
    ctx: Context,
    client_id: str,
    flow_id: str,
    artifact: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Fetch rows from a flow's named artifact output."""
    _require_tasking(ctx)
    rows = _vql(
        "SELECT * FROM source(client_id=client_id, flow_id=flow_id, artifact=artifact) "
        "LIMIT limit",
        env={
            "client_id": client_id,
            "flow_id": flow_id,
            "artifact": artifact,
            "limit": str(max(1, min(limit, 10000))),
        },
    )
    return rows


@mcp.tool()
def run_vql(
    ctx: Context,
    query: str,
    env: dict[str, str] | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Execute arbitrary VQL. Requires x-active-authorization."""
    _require_tasking(ctx)
    if not _active_authorized(ctx):
        raise PermissionError(
            "run_vql requires x-active-authorization — supervisor sets this from "
            "tasking.authorization."
        )
    # Wrap caller query to cap row count even if they omitted LIMIT.
    wrapped = f"SELECT * FROM chain(a={{ {query} }}) LIMIT {max(1, min(limit, 100000))}"
    return _vql(wrapped, env=env)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
