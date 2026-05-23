"""HuntDispatch — Protocol the Hunt nodes call to reach tools.

Phase 4 kickoff keeps wiring abstract. `StubDispatch` returns shape-correct
empty results so the graph is unit-testable without the knowledge spine up.
Phase 4.1 plugs a `LiveDispatch` that holds MCP clients for Wazuh (via
`mcp-server-wazuh`) + OpenCTI (for triage context) + TheHive (for case
escalation) plus pySigma for rule translation.

Contract — each method:
    - Accepts the typed object it needs.
    - Returns a list / typed object; never raises for a normal empty result.
    - Synchronous in this kickoff.
"""

from __future__ import annotations

from typing import Protocol

from schemas.hunt import (
    Hit,
    HuntCase,
    Hypothesis,
    HypothesisKind,
    SigmaQuery,
    Triage,
    TriagedHit,
)
from schemas.tasking import Tasking, TaskingType


class HuntDispatch(Protocol):
    """What each Hunt node needs from the outside world."""

    def plan_hypotheses(self, tasking: Tasking) -> list[Hypothesis]:
        """Generate hypotheses from the tasking (OTRF playbook + ATT&CK + LLM)."""

    def write_queries(self, hypothesis: Hypothesis) -> list[SigmaQuery]:
        """Emit one or more pySigma-translated queries per hypothesis."""

    def execute_query(self, query: SigmaQuery) -> list[Hit]:
        """Run a SigmaQuery against Wazuh / OpenSearch."""

    def triage_hit(self, hit: Hit) -> TriagedHit:
        """Correlate a raw hit against OpenCTI context; score + classify."""

    def open_case(self, tasking_id: str, triaged: list[TriagedHit]) -> HuntCase:
        """Open a TheHive case for escalated hits."""

    def narrate(
        self,
        tasking_id: str,
        triaged: list[TriagedHit],
        case: HuntCase | None,
    ) -> str:
        """LLM summary of the hunt run."""


class StubDispatch:
    """Default dispatch for unit tests and pre-Phase-4.1 scaffold runs."""

    def plan_hypotheses(self, tasking: Tasking) -> list[Hypothesis]:
        if tasking.type is not TaskingType.HUNT_TTP:
            return []
        # One canonical IOC-sweep hypothesis per target keeps the graph's
        # downstream stages exercised under StubDispatch.
        return [
            Hypothesis(
                kind=HypothesisKind.IOC_SWEEP,
                title=f"Sweep logs for {t.kind.value}:{t.value}",
                ttp=None,
                rationale="stub — replace with OTRF-playbook + LLM planner in 4.1",
                tlp=tasking.tlp,
            )
            for t in tasking.targets
        ]

    def write_queries(self, hypothesis: Hypothesis) -> list[SigmaQuery]:
        return []

    def execute_query(self, query: SigmaQuery) -> list[Hit]:
        return []

    def triage_hit(self, hit: Hit) -> TriagedHit:
        return TriagedHit(
            hit=hit,
            triage=Triage.BENIGN,
            confidence=0,
            context={},
            notes="stub dispatch — no OpenCTI lookup performed",
        )

    def open_case(self, tasking_id: str, triaged: list[TriagedHit]) -> HuntCase:
        # Not reached under StubDispatch because the escalator only calls
        # this when thresholds are met; stubs never produce enough hits.
        return HuntCase(
            case_id=f"stub-case-{tasking_id[:8]}",
            case_url=None,
            title="stub hunt case",
            severity=2,
            hit_ids=[t.hit.hit_id for t in triaged],
        )

    def narrate(
        self,
        tasking_id: str,
        triaged: list[TriagedHit],
        case: HuntCase | None,
    ) -> str:
        confirmed = sum(1 for t in triaged if t.triage is Triage.CONFIRMED)
        suspicious = sum(1 for t in triaged if t.triage is Triage.SUSPICIOUS)
        return (
            f"Hunt run {tasking_id}: {len(triaged)} triaged hit(s) "
            f"(confirmed={confirmed}, suspicious={suspicious}); "
            f"case={'opened' if case else 'none'}. "
            "(stub dispatch — no Wazuh / OpenCTI / TheHive calls made)"
        )
