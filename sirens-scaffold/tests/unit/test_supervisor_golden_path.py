"""Phase 2 exit gate — supervisor golden path.

Contract:
    Given a well-scoped Tasking and a matching allow-list,
    the supervisor advances intake → plan → dispatch → finalize,
    emits a STATUS message, and reaches done=True with zero violations.

If this test fails, Phase 2 does NOT exit.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from agents.supervisor import build_supervisor_graph
from agents.supervisor.policy import (
    ApprovalRecord,
    Approvals,
    Collectors,
    EngagementMeta,
    ScopeAllowlist,
    TargetSet,
)
from schemas.agent_message import PayloadType
from schemas.tasking import Posture, Target, TargetKind, Tasking, TaskingType


@pytest.fixture
def allowlist() -> ScopeAllowlist:
    now = datetime.now(timezone.utc)
    return ScopeAllowlist(
        allowlist_id="test-golden-path",
        engagement=EngagementMeta(
            customer="TestCo",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=30),
        ),
        approvals=Approvals(
            legal=ApprovalRecord(approver="counsel@testco", approved_at=now),
        ),
        posture=Posture.PASSIVE_PUBLIC,
        targets=TargetSet(
            report_urls=["https://thedfirreport.com/2026/01/example"],
            actors=["Scattered Spider"],
        ),
        collectors=Collectors(enabled=["abuse_ch.malwarebazaar", "alienvault.otx"]),
    )


@pytest.fixture
def tasking() -> Tasking:
    return Tasking(
        requester="analyst@sirens",
        type=TaskingType.INGEST_REPORT,
        targets=[
            Target(
                kind=TargetKind.REPORT_URL,
                value="https://thedfirreport.com/2026/01/example",
            )
        ],
        posture=Posture.PASSIVE_PUBLIC,
    )


def test_golden_path(allowlist: ScopeAllowlist, tasking: Tasking) -> None:
    app = build_supervisor_graph(allowlist)
    result = app.invoke({"tasking": tasking, "run_id": uuid4()})

    assert result["done"] is True, result
    assert result.get("violations", []) == [], result["violations"]
    assert result["next_swarm"] == "research"

    messages = result.get("messages", [])
    assert len(messages) == 1
    msg = messages[0]
    assert msg.payload_type is PayloadType.STATUS
    assert msg.payload == {"dispatched_to": "research"}
    assert msg.from_agent == "supervisor.dispatch"


def test_out_of_scope_target_blocks(allowlist: ScopeAllowlist) -> None:
    """A target not in the allow-list must produce a scope violation and short-circuit."""
    tasking = Tasking(
        requester="analyst@sirens",
        type=TaskingType.INGEST_REPORT,
        targets=[
            Target(
                kind=TargetKind.REPORT_URL,
                value="https://somewhere-not-allowed.example/",
            )
        ],
        posture=Posture.PASSIVE_PUBLIC,
    )
    app = build_supervisor_graph(allowlist)
    result = app.invoke({"tasking": tasking, "run_id": uuid4()})

    assert result["done"] is True
    assert any(v["kind"] == "scope" for v in result["violations"])
    assert result.get("next_swarm") is None
    assert result.get("messages", []) == []


def test_posture_mismatch_blocks(allowlist: ScopeAllowlist) -> None:
    """Posture upgrade without allow-list change must be rejected by ethics."""
    tasking = Tasking(
        requester="analyst@sirens",
        type=TaskingType.DEPLOY_DECEPTION,
        targets=[
            Target(kind=TargetKind.DOMAIN, value="decoy.testco.local"),
        ],
        posture=Posture.DECEPTION_INTERNAL,
    )
    app = build_supervisor_graph(allowlist)
    result = app.invoke({"tasking": tasking, "run_id": uuid4()})

    assert result["done"] is True
    kinds = {v["kind"] for v in result["violations"]}
    assert "scope" in kinds  # posture mismatch shows up as scope violation
