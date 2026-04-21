"""Sirens MCP server for self-hosted Canarytokens.

Targets the OSS `thinkst/canarytokens` stack (typically deployed via
`canarytokens-docker`). Exposes generation, history, and disable.

Surface:
    - list_token_types     — supported token kinds
    - create_token         — issue a new token
    - get_token_history    — fetch alerts / hits for a token
    - disable_token        — stop a token from alerting

Webhook enforcement: `webhook_url` is only allowed if its scheme+host
is in the `$CANARYTOKENS_ALLOWED_WEBHOOK_HOSTS` allow-list. This stops
a compromised agent from redirecting canary alerts to an attacker-owned
endpoint. The supervisor normally injects the Sirens audit sink as the
webhook, so the allow-list should list that host only.
"""

from __future__ import annotations

import os
from enum import Enum
from urllib.parse import urlparse

import httpx
import structlog
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field


log = structlog.get_logger("sirens.mcp.canarytokens")

CANARYTOKENS_URL = os.environ.get("CANARYTOKENS_URL", "http://canarytokens:8080")
CANARYTOKENS_TIMEOUT = float(os.environ.get("CANARYTOKENS_TIMEOUT", "30"))
ALLOWED_WEBHOOK_HOSTS = {
    h.strip().lower()
    for h in os.environ.get("CANARYTOKENS_ALLOWED_WEBHOOK_HOSTS", "").split(",")
    if h.strip()
}


mcp = FastMCP("sirens-canarytokens", dependencies=["httpx", "pydantic"])


class TokenType(str, Enum):
    DNS = "dns"
    WEB = "web"
    AWS_ID = "aws-id"
    QR_CODE = "qr-code"
    WINDOWS_DIR = "windows-dir"
    PDF_ACROBAT = "pdf-acrobat-reader"
    WORD = "word"
    SQL = "sql-db"
    CLONED_SITE = "clonedsite"
    WIREGUARD = "wireguard"
    SLACK_API = "slack-api"
    MYSQL = "my-sql"
    SVG = "svg"
    SMTP = "smtp"
    KUBECONFIG = "kubeconfig"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=CANARYTOKENS_URL,
        timeout=CANARYTOKENS_TIMEOUT,
        headers={"User-Agent": "sirens-mcp-canarytokens/0.1"},
    )


def _require_tasking(ctx: Context) -> str:
    headers = getattr(ctx, "request_headers", {}) or {}
    tid = headers.get("x-tasking-id") or headers.get("X-Tasking-Id")
    if not tid:
        raise ValueError("x-tasking-id header required — supervisor must set it")
    return tid


def _webhook_allowed(url: str | None) -> bool:
    if not url:
        return True
    if not ALLOWED_WEBHOOK_HOSTS:
        # Default-deny unless explicitly configured.
        return False
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return host.lower() in ALLOWED_WEBHOOK_HOSTS


# ---------- Schemas ----------


class CreateTokenInput(BaseModel):
    token_type: TokenType = Field(..., description="Canarytoken kind")
    memo: str = Field(..., min_length=1, max_length=1000)
    email: str | None = None
    webhook_url: str | None = None
    # Extra params passed through (type-specific), e.g. cloned_web, redirect_url.
    extra: dict[str, str] = Field(default_factory=dict)


class Token(BaseModel):
    token: str
    token_type: str
    canarytoken: str | None = None  # the trigger-side identifier (DNS name, URL, etc.)
    auth: str | None = None          # management secret
    memo: str
    triggered_count: int | None = None
    url_components: list[str] = Field(default_factory=list)


class TokenHit(BaseModel):
    time_of_hit: str
    input_channel: str | None = None
    src_ip: str | None = None
    geo_info: dict[str, str | float] = Field(default_factory=dict)
    useragent: str | None = None
    additional: dict[str, str] = Field(default_factory=dict)


# ---------- Tools ----------


@mcp.tool()
def list_token_types(ctx: Context) -> list[str]:
    """Enumerate the token kinds this server understands."""
    _require_tasking(ctx)
    return [t.value for t in TokenType]


@mcp.tool()
async def create_token(ctx: Context, payload: CreateTokenInput) -> Token:
    """Generate a new canarytoken."""
    _require_tasking(ctx)
    if not _webhook_allowed(payload.webhook_url):
        raise PermissionError(
            f"webhook host not in CANARYTOKENS_ALLOWED_WEBHOOK_HOSTS "
            f"(configured: {sorted(ALLOWED_WEBHOOK_HOSTS) or 'empty'})"
        )

    form: dict[str, str] = {
        "type": payload.token_type.value,
        "memo": payload.memo,
    }
    if payload.email:
        form["email"] = payload.email
    if payload.webhook_url:
        form["webhook_url"] = payload.webhook_url
    form.update(payload.extra)

    async with _client() as http:
        r = await http.post("/generate", data=form)
        r.raise_for_status()
        data = r.json()

    return Token(
        token=data.get("Token", ""),
        token_type=payload.token_type.value,
        canarytoken=data.get("Hostname") or data.get("Url"),
        auth=data.get("Auth"),
        memo=payload.memo,
        url_components=[u for u in [data.get("Url"), data.get("Hostname")] if u],
    )


@mcp.tool()
async def get_token_history(ctx: Context, token: str, auth: str) -> list[TokenHit]:
    """Fetch alerts for a token. `auth` is the management secret from create_token."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.get("/history", params={"token": token, "auth": auth})
        r.raise_for_status()
        data = r.json()
    hits = data.get("hits") or data.get("history") or []
    return [
        TokenHit(
            time_of_hit=str(h.get("time_of_hit") or h.get("time") or ""),
            input_channel=h.get("input_channel"),
            src_ip=h.get("src_ip") or h.get("src"),
            geo_info=h.get("geo_info") or {},
            useragent=h.get("useragent"),
            additional={k: str(v) for k, v in (h.get("additional_info") or {}).items()},
        )
        for h in hits
    ]


@mcp.tool()
async def disable_token(ctx: Context, token: str, auth: str) -> dict[str, str]:
    """Stop a token from alerting. Idempotent."""
    _require_tasking(ctx)
    async with _client() as http:
        r = await http.post(
            "/manage",
            data={"token": token, "auth": auth, "action": "disable"},
        )
        r.raise_for_status()
    return {"token": token, "status": "disabled"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
