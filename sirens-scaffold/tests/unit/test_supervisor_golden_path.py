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
from schemas.agent_message import AgentMessage, Audit, PayloadType, ToolCall
from schemas.tasking import Budget, Posture, Target, TargetKind, Tasking, TaskingType


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

    # After Phase 3 hand-off: supervisor emits a STATUS preamble, then the
    # Research subgraph runs and appends its own REPORT message.
    messages = result.get("messages", [])
    assert len(messages) == 2, messages

    status = messages[0]
    assert status.payload_type is PayloadType.STATUS
    assert status.payload == {"dispatched_to": "research"}
    assert status.from_agent == "supervisor.dispatch"

    report = messages[1]
    assert report.payload_type is PayloadType.REPORT
    assert report.from_agent == "research.reporter"
    assert report.swarm == "research"
    assert report.payload["observable_count"] == 0  # StubDispatch, no live data


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


# ---------- ledger-merge tests -------------------------------------------


class _FakeSubgraph:
    """Minimal object matching the `swarms[name].invoke(...)` contract."""

    def __init__(self, messages: list[AgentMessage]) -> None:
        self._messages = messages

    def invoke(self, _state: dict) -> dict:
        return {"messages": self._messages}


def _spend_message(tasking_id, *, in_tok: int, out_tok: int, cost: float,
                   calls: int = 0) -> AgentMessage:
    """Build a REPORT message with a populated Audit block."""
    now = datetime.now(timezone.utc)
    return AgentMessage(
        tasking_id=tasking_id,
        from_agent="research.reporter",
        to_agent=None,
        swarm="research",
        payload_type=PayloadType.REPORT,
        payload={"stub": True},
        audit=Audit(
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=cost,
            tool_calls=[
                ToolCall(
                    tool=f"fake.tool.{i}",
                    started_at=now,
                    duration_ms=10,
                    cost_usd=0.0,
                    success=True,
                )
                for i in range(calls)
            ],
        ),
    )


def test_dispatch_folds_subgraph_audit_into_ledger(
    allowlist: ScopeAllowlist, tasking: Tasking
) -> None:
    """Subgraph audit totals must reach the supervisor ledger before finalize."""
    fake = _FakeSubgraph(
        [_spend_message(tasking.tasking_id, in_tok=1234, out_tok=567,
                        cost=0.42, calls=3)]
    )
    app = build_supervisor_graph(allowlist, swarms={"research": fake})
    result = app.invoke({"tasking": tasking, "run_id": uuid4()})

    assert result["done"] is True
    assert result.get("violations", []) == []

    ledger = result["ledger"]
    assert ledger["input_tokens"] == 1234
    assert ledger["output_tokens"] == 567
    assert ledger["cost_usd"] == pytest.approx(0.42)
    assert ledger["tool_calls"] == 3


def test_subgraph_overspend_trips_budget_gate(
    allowlist: ScopeAllowlist,
) -> None:
    """A tight Budget plus subgraph cost must produce a budget violation at finalize."""
    tight = Tasking(
        requester="analyst@sirens",
        type=TaskingType.INGEST_REPORT,
        targets=[
            Target(kind=TargetKind.REPORT_URL,
                   value="https://thedfirreport.com/2026/01/example"),
        ],
        posture=Posture.PASSIVE_PUBLIC,
        budget=Budget(
            max_input_tokens=1_000,
            max_output_tokens=1_000,
            max_cost_usd=1.0,
        ),
    )
    fake = _FakeSubgraph(
        # 2000 input tokens blows the 1000 ceiling; cost_usd 5.00 blows $1.
        [_spend_message(tight.tasking_id, in_tok=2_000, out_tok=100, cost=5.0)]
    )
    app = build_supervisor_graph(allowlist, swarms={"research": fake})
    result = app.invoke({"tasking": tight, "run_id": uuid4()})

    assert result["done"] is True
    kinds = {v["kind"] for v in result.get("violations", [])}
    assert "budget" in kinds, result.get("violations")

    ledger = result["ledger"]
    assert ledger["input_tokens"] == 2_000
    assert ledger["cost_usd"] == pytest.approx(5.0)
