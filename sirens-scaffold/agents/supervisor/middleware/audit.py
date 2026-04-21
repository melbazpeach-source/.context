"""Audit log writer.

Every state transition appends a JSON record to the audit log. In production,
point `AUDIT_SINK` at a durable store (Postgres, object storage, SIEM).
Dev default: structlog to stderr.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from agents.supervisor.state import SupervisorState


_logger = structlog.get_logger("sirens.supervisor.audit")


def _sink() -> Path | None:
    raw = os.environ.get("SIRENS_AUDIT_SINK")
    if not raw:
        return None
    p = Path(raw)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_audit(state: SupervisorState, event: str, **extra: Any) -> None:
    """Record one event. Never raises — audit failure must not break flow."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "run_id": str(state.get("run_id")) if state.get("run_id") else None,
        "tasking_id": (
            str(state["tasking"].tasking_id) if state.get("tasking") else None
        ),
        "current_step": state.get("current_step"),
        "ledger": state.get("ledger"),
        "violations": state.get("violations", []),
        **extra,
    }
    try:
        sink = _sink()
        if sink is not None:
            with sink.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        else:
            _logger.info(event, **record)
    except Exception as exc:  # noqa: BLE001 — audit is best-effort
        _logger.warning("audit_write_failed", error=str(exc))
