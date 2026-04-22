"""ResearchDispatch — Protocol nodes call to reach tools.

The Research swarm depends on five MCP brokers plus a handful of direct APIs.
Phase 3 kickoff keeps the wiring abstract: nodes call a `ResearchDispatch`.
`StubDispatch` returns empty results so the graph is unit-testable without
bringing up the full stack. Phase 3.1 plugs in a `LiveDispatch` that holds
MCP clients.

Contract — each method:
    - Accepts the typed query/observable it needs.
    - Returns a list (possibly empty) — never raises for a normal empty result.
    - Is synchronous in this kickoff; Phase 3.1 may switch to async.
"""

from __future__ import annotations

from typing import Any, Protocol

from schemas.research import (
    Campaign,
    EnrichedObservable,
    Observable,
    ResearchQuery,
)


class ResearchDispatch(Protocol):
    """What each Research node needs from the outside world."""

    def collect(self, query: ResearchQuery) -> list[Observable]:
        """Collector fan-out. Invoked once per ResearchQuery."""

    def enrich(self, observable: Observable) -> EnrichedObservable:
        """IntelOwl submit_observable + poll. One call per Observable."""

    def correlate(
        self,
        tasking_id: str,
        enriched: list[EnrichedObservable],
    ) -> Campaign | None:
        """OpenCTI pivot. Returns a Campaign or None if nothing to anchor."""

    def narrate(
        self,
        tasking_id: str,
        campaign: Campaign | None,
        enriched: list[EnrichedObservable],
    ) -> str:
        """LLM summary. Returns a narrative string (may be empty)."""

    def build_stix_bundle(
        self,
        tasking_id: str,
        campaign: Campaign | None,
        enriched: list[EnrichedObservable],
    ) -> dict[str, Any]:
        """Assemble a STIX 2.1 bundle. Shape-valid even when inputs are empty."""


class StubDispatch:
    """Default dispatch used in unit tests and before Phase 3.1 wiring.

    Every method returns shape-correct empty results. Using the swarm with
    StubDispatch verifies graph wiring without touching any live tool.
    """

    def collect(self, query: ResearchQuery) -> list[Observable]:
        return []

    def enrich(self, observable: Observable) -> EnrichedObservable:
        from schemas.research import EnrichedObservable, Verdict

        return EnrichedObservable(
            observable=observable,
            analyzers={},
            verdict=Verdict.UNKNOWN,
            tags=[],
        )

    def correlate(
        self,
        tasking_id: str,
        enriched: list[EnrichedObservable],
    ) -> Campaign | None:
        return None

    def narrate(
        self,
        tasking_id: str,
        campaign: Campaign | None,
        enriched: list[EnrichedObservable],
    ) -> str:
        return (
            f"Research run {tasking_id}: "
            f"{len(enriched)} enriched observable(s); "
            f"campaign={'yes' if campaign else 'none'}. "
            "(stub dispatch — no live tool calls)"
        )

    def build_stix_bundle(
        self,
        tasking_id: str,
        campaign: Campaign | None,
        enriched: list[EnrichedObservable],
    ) -> dict[str, Any]:
        return {
            "type": "bundle",
            "id": f"bundle--{tasking_id}",
            "objects": [],
        }
