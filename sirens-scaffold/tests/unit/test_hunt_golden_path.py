"""Phase 4 exit gate — Hunt-swarm golden path.

Contract (kickoff):
    Given a HUNT_TTP Tasking, the Hunt swarm advances
        hypothesis_planner → query_writer → hunter → triage → escalator,
    produces a typed HuntReport, and reaches done=True.

    With StubDispatch, queries/hits/triaged are empty (no Wazuh backend);
    the test proves WIRING, not live data. Phase 4.1 replaces StubDispatch
    with LiveDispatch and adds integration tests behind `integration`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from agents.hunt import build_hunt_graph
from agents.hunt.dispatch import StubDispatch
from schemas.agent_message import PayloadType
from schemas.hunt import (
    Hit,
    HuntCase,
    Hypothesis,
    HypothesisKind,
    SigmaQuery,
    Triage,
    TriagedHit,
)
from schemas.tasking import Posture, Target, TargetKind, Tasking, TaskingType


@pytest.fixture
def hunt_tasking() -> Tasking:
    return Tasking(
        requester="analyst@sirens",
        type=TaskingType.HUNT_TTP,
        targets=[
            Target(kind=TargetKind.CVE, value="CVE-2026-0001"),
            Target(kind=TargetKind.MALWARE_FAMILY, value="AkiraRansomware"),
        ],
        posture=Posture.PASSIVE_PUBLIC,
    )


def test_golden_path(hunt_tasking: Tasking) -> None:
    app = build_hunt_graph()
    result = app.invoke({"tasking": hunt_tasking, "run_id": uuid4()})

    assert result["done"] is True, result
    assert result["current_step"] == "escalator"

    # One hypothesis per target under StubDispatch.
    hypotheses = result.get("hypotheses", [])
    assert len(hypotheses) == len(hunt_tasking.targets)
    assert all(h.kind is HypothesisKind.IOC_SWEEP for h in hypotheses)

    # Downstream stubs yield empties — shape, not data.
    assert result.get("queries", []) == []
    assert result.get("hits", []) == []
    assert result.get("triaged", []) == []
    assert result.get("case") is None

    messages = result.get("messages", [])
    assert len(messages) == 1
    msg = messages[0]
    assert msg.payload_type is PayloadType.REPORT
    assert msg.from_agent == "hunt.escalator"
    assert msg.swarm == "hunt"
    assert msg.payload["case_opened"] is False
    assert msg.payload["hit_count"] == 0

    report = result["report"]
    assert report.tasking_id == hunt_tasking.tasking_id
    assert report.case is None
    assert report.narrative


def test_non_hunt_tasking_short_circuits_to_escalator() -> None:
    """A tasking that isn't HUNT_TTP yields zero hypotheses → straight to escalator."""
    tasking = Tasking(
        requester="analyst@sirens",
        type=TaskingType.TRACK_ACTOR,   # not hunt
        targets=[Target(kind=TargetKind.ACTOR, value="Scattered Spider")],
        posture=Posture.PASSIVE_PUBLIC,
    )
    app = build_hunt_graph()
    result = app.invoke({"tasking": tasking, "run_id": uuid4()})

    assert result["done"] is True
    assert result["current_step"] == "escalator"
    assert result.get("hypotheses", []) == []
    assert result.get("queries", []) == []
    assert result["report"].narrative


def test_escalator_opens_case_over_threshold(hunt_tasking: Tasking) -> None:
    """Enough CONFIRMED hits must trip the threshold and produce a HuntCase."""

    class FakeDispatch(StubDispatch):
        def write_queries(self, hypothesis: Hypothesis) -> list[SigmaQuery]:
            return [
                SigmaQuery(
                    hypothesis_id=hypothesis.hypothesis_id,
                    sigma_rule_id="sirens-test-0001",
                    rule_yaml="title: test\n",
                    backend="opensearch-wazuh",
                    translated="*",
                    index_patterns=["ecs-logs-*"],
                )
            ]

        def execute_query(self, query: SigmaQuery) -> list[Hit]:
            # 3 hits per query, and there are len(hypotheses) queries.
            return [
                Hit(
                    query_id=query.query_id,
                    timestamp=datetime.now(timezone.utc),
                    source="wazuh-indexer",
                    host=f"host-{i}",
                    user="svc-account",
                    raw={"event": f"stub-{i}"},
                )
                for i in range(3)
            ]

        def triage_hit(self, hit: Hit) -> TriagedHit:
            return TriagedHit(
                hit=hit,
                triage=Triage.CONFIRMED,
                confidence=90,
                context={"actor": "test-actor"},
                notes="fake dispatch",
            )

        def open_case(
            self, tasking_id: str, triaged: list[TriagedHit]
        ) -> HuntCase:
            return HuntCase(
                case_id=f"TH-{tasking_id[:8]}",
                case_url=f"https://thehive.local/cases/TH-{tasking_id[:8]}",
                title=f"Sirens hunt — {len(triaged)} confirmed hits",
                severity=3,
                hit_ids=[t.hit.hit_id for t in triaged],
            )

    app = build_hunt_graph(FakeDispatch())
    result = app.invoke({"tasking": hunt_tasking, "run_id": uuid4()})

    assert result["done"] is True
    # 2 targets → 2 hypotheses → 2 queries → 6 hits → 6 triaged (all CONFIRMED).
    assert len(result["hypotheses"]) == 2
    assert len(result["queries"]) == 2
    assert len(result["hits"]) == 6
    assert len(result["triaged"]) == 6
    assert all(t.triage is Triage.CONFIRMED for t in result["triaged"])

    case = result["case"]
    assert case is not None
    assert case.case_id.startswith("TH-")
    assert case.severity == 3

    msg = result["messages"][0]
    assert msg.payload["case_opened"] is True
    assert msg.payload["case_id"] == case.case_id
    assert msg.payload["escalatable_count"] == 6


def test_below_threshold_does_not_open_case(hunt_tasking: Tasking) -> None:
    """Triage below the escalation threshold must NOT open a case."""

    class OneHitDispatch(StubDispatch):
        def write_queries(self, hypothesis: Hypothesis) -> list[SigmaQuery]:
            return [
                SigmaQuery(
                    hypothesis_id=hypothesis.hypothesis_id,
                    rule_yaml="title: test\n",
                    backend="opensearch-wazuh",
                    translated="*",
                    index_patterns=["ecs-logs-*"],
                )
            ]

        def execute_query(self, query: SigmaQuery) -> list[Hit]:
            # 1 hit per query → 2 total < threshold 3.
            return [
                Hit(
                    query_id=query.query_id,
                    timestamp=datetime.now(timezone.utc),
                    source="wazuh-indexer",
                )
            ]

        def triage_hit(self, hit: Hit) -> TriagedHit:
            return TriagedHit(hit=hit, triage=Triage.SUSPICIOUS, confidence=60)

    app = build_hunt_graph(OneHitDispatch(), escalation_threshold=3)
    result = app.invoke({"tasking": hunt_tasking, "run_id": uuid4()})

    assert result["done"] is True
    assert result.get("case") is None
    msg = result["messages"][0]
    assert msg.payload["case_opened"] is False
    assert msg.payload["escalatable_count"] == 2
