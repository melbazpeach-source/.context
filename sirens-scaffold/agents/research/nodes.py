"""Research-swarm LangGraph nodes.

Planner → Collector → Enricher → Correlator → Analyst → Reporter.

Every node is a closure built by a `make_*` factory so it can capture the
shared `ResearchDispatch`. Nodes stay thin — logic belongs in dispatch
implementations or upstream policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from agents.research.dispatch import ResearchDispatch
from agents.research.state import ResearchState
from agents.supervisor.middleware.audit import write_audit
from schemas.agent_message import AgentMessage, PayloadType
from schemas.research import (
    QueryKind,
    ResearchQuery,
    ResearchReport,
)
from schemas.tasking import TargetKind, TaskingType


# ----- Planner ------------------------------------------------------------


# Mapping from TaskingType → which QueryKinds the Planner should emit.
# The Planner still filters by Target.kind so we never ask a malware DB
# about an actor alias.
_PLAN_BY_TASKING: dict[TaskingType, list[QueryKind]] = {
    TaskingType.TRACK_ACTOR: [
        QueryKind.INFRA,
        QueryKind.MALWARE,
        QueryKind.PASSIVE_DNS,
        QueryKind.TI_PLATFORM,
        QueryKind.DARK_WEB,
        QueryKind.SOCIAL,
    ],
    TaskingType.WATCH_LEAK: [
        QueryKind.LEAK,
        QueryKind.SOCIAL,
        QueryKind.DARK_WEB,
    ],
    TaskingType.INGEST_REPORT: [
        QueryKind.MALWARE,
        QueryKind.INFRA,
        QueryKind.TI_PLATFORM,
    ],
    TaskingType.ENRICH_OBSERVABLE: [
        QueryKind.MALWARE,
        QueryKind.INFRA,
        QueryKind.PASSIVE_DNS,
        QueryKind.TI_PLATFORM,
    ],
    TaskingType.HUNT_TTP: [
        QueryKind.CVE,
        QueryKind.TI_PLATFORM,
    ],
}


# Which ObservableKind → which sources the Collector is expected to use.
# Strings are symbolic; Phase 3.1 dispatch maps them to MCP tool calls.
_SOURCES_BY_QUERY: dict[QueryKind, list[str]] = {
    QueryKind.INFRA: ["shodan", "censys", "greynoise", "spiderfoot"],
    QueryKind.MALWARE: ["abuse_ch.malwarebazaar", "abuse_ch.urlhaus",
                        "abuse_ch.threatfox", "virustotal"],
    QueryKind.PASSIVE_DNS: ["dnsdb", "domaintools", "mnemonic"],
    QueryKind.TI_PLATFORM: ["alienvault.otx", "opencti", "misp_feeds"],
    QueryKind.LEAK: ["gitguardian", "github_dorks"],
    QueryKind.SOCIAL: ["mastodon", "telegram_public", "reddit_netsec"],
    QueryKind.DARK_WEB: ["ahmia", "deepdarkCTI"],
    QueryKind.CVE: ["nvd", "cisa_kev", "vulncheck", "poc_in_github"],
    QueryKind.DECEPTION: ["canarytokens", "opencanary", "mhn"],
}


# Only target kinds that make sense per query kind. Filters out nonsense
# queries like "ask Shodan about an actor alias".
_QUERY_KIND_ACCEPTS: dict[QueryKind, set[TargetKind]] = {
    QueryKind.INFRA: {TargetKind.IP, TargetKind.DOMAIN, TargetKind.ASN, TargetKind.URL},
    QueryKind.MALWARE: {TargetKind.FILE_HASH, TargetKind.URL, TargetKind.DOMAIN,
                        TargetKind.MALWARE_FAMILY},
    QueryKind.PASSIVE_DNS: {TargetKind.DOMAIN, TargetKind.IP},
    QueryKind.TI_PLATFORM: set(TargetKind),  # TI platforms index everything
    QueryKind.LEAK: {TargetKind.DOMAIN, TargetKind.EMAIL, TargetKind.ACTOR,
                    TargetKind.CAMPAIGN},
    QueryKind.SOCIAL: {TargetKind.ACTOR, TargetKind.CAMPAIGN, TargetKind.MALWARE_FAMILY,
                       TargetKind.CVE},
    QueryKind.DARK_WEB: {TargetKind.ACTOR, TargetKind.CAMPAIGN,
                         TargetKind.MALWARE_FAMILY},
    QueryKind.CVE: {TargetKind.CVE},
    QueryKind.DECEPTION: {TargetKind.DOMAIN, TargetKind.IP},
}


def make_planner() -> Callable[[ResearchState], dict]:
    def planner(state: ResearchState) -> dict:
        tasking = state["tasking"]
        kinds = _PLAN_BY_TASKING.get(tasking.type, [QueryKind.TI_PLATFORM])

        queries: list[ResearchQuery] = []
        for target in tasking.targets:
            for kind in kinds:
                if target.kind not in _QUERY_KIND_ACCEPTS[kind]:
                    continue
                queries.append(
                    ResearchQuery(
                        kind=kind,
                        target=target,
                        sources=list(_SOURCES_BY_QUERY[kind]),
                        tlp=tasking.tlp,
                        rationale=f"tasking={tasking.type.value}",
                    )
                )

        update = {
            "current_step": "planner",
            "queries": queries,
        }
        write_audit(
            {**state, **update},
            event="research.plan",
            query_count=len(queries),
        )
        return update

    return planner


# ----- Collector ---------------------------------------------------------


def make_collector(dispatch: ResearchDispatch) -> Callable[[ResearchState], dict]:
    def collector(state: ResearchState) -> dict:
        out = []
        for query in state.get("queries", []):
            out.extend(dispatch.collect(query))

        update = {
            "current_step": "collector",
            "observables": out,
        }
        write_audit(
            {**state, **update},
            event="research.collect",
            query_count=len(state.get("queries", [])),
            observable_count=len(out),
        )
        return update

    return collector


# ----- Enricher ----------------------------------------------------------


def make_enricher(dispatch: ResearchDispatch) -> Callable[[ResearchState], dict]:
    def enricher(state: ResearchState) -> dict:
        enriched = [dispatch.enrich(o) for o in state.get("observables", [])]

        update = {
            "current_step": "enricher",
            "enriched": enriched,
        }
        write_audit(
            {**state, **update},
            event="research.enrich",
            enriched_count=len(enriched),
        )
        return update

    return enricher


# ----- Correlator --------------------------------------------------------


def make_correlator(dispatch: ResearchDispatch) -> Callable[[ResearchState], dict]:
    def correlator(state: ResearchState) -> dict:
        tasking_id = str(state["tasking"].tasking_id)
        campaign = dispatch.correlate(tasking_id, state.get("enriched", []))

        update: dict = {
            "current_step": "correlator",
            "campaign": campaign,
        }
        write_audit(
            {**state, **update},
            event="research.correlate",
            has_campaign=campaign is not None,
        )
        return update

    return correlator


# ----- Analyst -----------------------------------------------------------


def make_analyst(dispatch: ResearchDispatch) -> Callable[[ResearchState], dict]:
    def analyst(state: ResearchState) -> dict:
        tasking_id = str(state["tasking"].tasking_id)
        narrative = dispatch.narrate(
            tasking_id,
            state.get("campaign"),
            state.get("enriched", []),
        )

        update = {
            "current_step": "analyst",
            "narrative": narrative,
        }
        write_audit(
            {**state, **update},
            event="research.analyse",
            narrative_chars=len(narrative or ""),
        )
        return update

    return analyst


# ----- Reporter ----------------------------------------------------------


def make_reporter(dispatch: ResearchDispatch) -> Callable[[ResearchState], dict]:
    def reporter(state: ResearchState) -> dict:
        tasking = state["tasking"]
        tasking_id = str(tasking.tasking_id)

        bundle = dispatch.build_stix_bundle(
            tasking_id,
            state.get("campaign"),
            state.get("enriched", []),
        )

        # When the zero-query shortcut bypassed the analyst, synthesise a
        # narrative here so the ResearchReport contract always holds.
        narrative = state.get("narrative") or dispatch.narrate(
            tasking_id,
            state.get("campaign"),
            state.get("enriched", []),
        )

        report = ResearchReport(
            tasking_id=tasking.tasking_id,
            narrative=narrative,
            campaign=state.get("campaign"),
            enriched=state.get("enriched", []),
            draft_detections=[],   # populated by Detection-Engineering swarm later
            stix_bundle=bundle,
            misp_event_json=None,  # wired in Phase 3.1 via sirens-mcp-misp
            thehive_case_ref=None, # HITL-gated; see runbook
            tlp=tasking.tlp,
        )

        msg = AgentMessage(
            tasking_id=tasking.tasking_id,
            from_agent="research.reporter",
            to_agent=None,
            swarm="research",
            payload_type=PayloadType.REPORT,
            payload={
                "report_id": str(report.report_id),
                "narrative": report.narrative,
                "observable_count": len(report.enriched),
                "has_campaign": report.campaign is not None,
            },
            markings=[tasking.tlp],
        )

        update = {
            "current_step": "reporter",
            "report": report,
            "messages": [msg],
            "done": True,
        }
        write_audit(
            {**state, **update},
            event="research.report",
            report_id=str(report.report_id),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        return update

    return reporter
