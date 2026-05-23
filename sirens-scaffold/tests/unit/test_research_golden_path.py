"""Phase 3 exit gate — Research-swarm golden path.

Contract (kickoff):
    Given a well-typed Tasking, the Research swarm advances
        planner → collector → enricher → correlator → analyst → reporter,
    produces a typed ResearchReport, and reaches done=True.

    With StubDispatch, counts of collected/enriched items are zero — the test
    proves WIRING, not live data. Phase 3.1 replaces StubDispatch with
    LiveDispatch and adds integration tests behind the `integration` marker.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from agents.research import build_research_graph
from agents.research.dispatch import StubDispatch
from schemas.agent_message import PayloadType, Provenance
from schemas.research import (
    EnrichedObservable,
    Observable,
    ObservableKind,
    ResearchQuery,
    Verdict,
)
from schemas.tasking import Posture, Target, TargetKind, Tasking, TaskingType


@pytest.fixture
def ingest_tasking() -> Tasking:
    return Tasking(
        requester="analyst@sirens",
        type=TaskingType.INGEST_REPORT,
        targets=[
            Target(
                kind=TargetKind.REPORT_URL,
                value="https://thedfirreport.com/2026/01/example",
            ),
            Target(kind=TargetKind.DOMAIN, value="example-c2.test"),
            Target(
                kind=TargetKind.FILE_HASH,
                value="44d88612fea8a8f36de82e1278abb02f",
            ),
        ],
        posture=Posture.PASSIVE_PUBLIC,
    )


def test_golden_path(ingest_tasking: Tasking) -> None:
    app = build_research_graph()
    result = app.invoke({"tasking": ingest_tasking, "run_id": uuid4()})

    assert result["done"] is True, result
    assert result["current_step"] == "reporter"

    # Planner produced at least one query per eligible (target, kind) pair.
    queries = result.get("queries", [])
    assert len(queries) > 0, "planner emitted no queries"
    # DOMAIN target is accepted by INFRA, MALWARE, TI_PLATFORM for INGEST_REPORT.
    # FILE_HASH is accepted by MALWARE + TI_PLATFORM. REPORT_URL is only TI.
    assert any(q.target.kind is TargetKind.REPORT_URL for q in queries)
    assert any(q.target.kind is TargetKind.DOMAIN for q in queries)
    assert any(q.target.kind is TargetKind.FILE_HASH for q in queries)

    # StubDispatch yields zero observables — the important property is shape.
    assert result.get("observables", []) == []
    assert result.get("enriched", []) == []
    assert result.get("campaign") is None

    # Reporter must emit a REPORT AgentMessage.
    messages = result.get("messages", [])
    assert len(messages) == 1
    msg = messages[0]
    assert msg.payload_type is PayloadType.REPORT
    assert msg.from_agent == "research.reporter"
    assert msg.payload["observable_count"] == 0
    assert msg.payload["has_campaign"] is False

    # The ResearchReport must be typed and carry a STIX bundle shell.
    report = result["report"]
    assert report.tasking_id == ingest_tasking.tasking_id
    assert report.stix_bundle["type"] == "bundle"
    assert report.stix_bundle["objects"] == []
    assert report.narrative  # stub produces a deterministic one-liner


def test_planner_skips_reporter_when_no_queries_match() -> None:
    """A tasking whose targets match no QueryKind still reaches reporter cleanly."""
    tasking = Tasking(
        requester="analyst@sirens",
        type=TaskingType.WATCH_LEAK,
        # WATCH_LEAK accepts LEAK/SOCIAL/DARK_WEB. ASN matches none of them.
        targets=[Target(kind=TargetKind.ASN, value="AS15169")],
        posture=Posture.PASSIVE_PUBLIC,
    )

    app = build_research_graph()
    result = app.invoke({"tasking": tasking, "run_id": uuid4()})

    assert result["done"] is True
    assert result["current_step"] == "reporter"
    assert result.get("queries", []) == []
    # The zero-query shortcut must skip collector/enricher/correlator/analyst.
    assert result.get("observables", []) == []
    assert result["report"].narrative  # reporter still emits a typed report


def test_reporter_integrates_dispatch_outputs() -> None:
    """Injecting a custom dispatch flows data through to the ResearchReport."""
    tasking = Tasking(
        requester="analyst@sirens",
        type=TaskingType.ENRICH_OBSERVABLE,
        targets=[Target(kind=TargetKind.IP, value="203.0.113.1")],
        posture=Posture.PASSIVE_PUBLIC,
    )

    class FakeDispatch(StubDispatch):
        def collect(self, query: ResearchQuery) -> list[Observable]:
            return [
                Observable(
                    kind=ObservableKind.IP,
                    value="203.0.113.1",
                    query_id=query.query_id,
                    provenance=Provenance(
                        source="test.fake",
                        collected_at=datetime.now(timezone.utc),
                    ),
                )
            ]

        def enrich(self, observable: Observable) -> EnrichedObservable:
            return EnrichedObservable(
                observable=observable,
                analyzers={"fake_analyzer": {"score": 9}},
                verdict=Verdict.MALICIOUS,
                tags=["c2"],
            )

    app = build_research_graph(FakeDispatch())
    result = app.invoke({"tasking": tasking, "run_id": uuid4()})

    # Planner emits one query per (IP target, accepting kind); each yields 1 obs.
    assert len(result["observables"]) == len(result["queries"])
    assert len(result["enriched"]) == len(result["observables"])
    assert all(e.verdict is Verdict.MALICIOUS for e in result["enriched"])

    report = result["report"]
    assert len(report.enriched) == len(result["observables"])
    assert report.narrative.startswith(f"Research run {tasking.tasking_id}")
