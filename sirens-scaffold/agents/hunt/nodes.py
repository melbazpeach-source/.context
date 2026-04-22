"""Hunt-swarm LangGraph nodes.

hypothesis_planner → query_writer → hunter → triage → escalator.

Factory-closure pattern mirrors Research: each `make_*` captures the shared
`HuntDispatch` and the threshold for case escalation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from agents.hunt.dispatch import HuntDispatch
from agents.hunt.state import HuntState
from agents.supervisor.middleware.audit import write_audit
from schemas.agent_message import AgentMessage, PayloadType
from schemas.hunt import HuntReport, Triage


# The escalator opens a TheHive case when the count of confirmed/suspicious
# triaged hits is at least this threshold. Overridable per-build.
DEFAULT_ESCALATION_THRESHOLD = 3


def make_hypothesis_planner(dispatch: HuntDispatch) -> Callable[[HuntState], dict]:
    def planner(state: HuntState) -> dict:
        hypotheses = dispatch.plan_hypotheses(state["tasking"])
        update = {
            "current_step": "hypothesis_planner",
            "hypotheses": hypotheses,
        }
        write_audit(
            {**state, **update},
            event="hunt.hypothesis_plan",
            hypothesis_count=len(hypotheses),
        )
        return update

    return planner


def make_query_writer(dispatch: HuntDispatch) -> Callable[[HuntState], dict]:
    def writer(state: HuntState) -> dict:
        out = []
        for h in state.get("hypotheses", []):
            out.extend(dispatch.write_queries(h))

        update = {
            "current_step": "query_writer",
            "queries": out,
        }
        write_audit(
            {**state, **update},
            event="hunt.write_queries",
            hypothesis_count=len(state.get("hypotheses", [])),
            query_count=len(out),
        )
        return update

    return writer


def make_hunter(dispatch: HuntDispatch) -> Callable[[HuntState], dict]:
    def hunter(state: HuntState) -> dict:
        out = []
        for q in state.get("queries", []):
            out.extend(dispatch.execute_query(q))

        update = {
            "current_step": "hunter",
            "hits": out,
        }
        write_audit(
            {**state, **update},
            event="hunt.execute",
            query_count=len(state.get("queries", [])),
            hit_count=len(out),
        )
        return update

    return hunter


def make_triage(dispatch: HuntDispatch) -> Callable[[HuntState], dict]:
    def triage(state: HuntState) -> dict:
        out = [dispatch.triage_hit(h) for h in state.get("hits", [])]

        update = {
            "current_step": "triage",
            "triaged": out,
        }
        write_audit(
            {**state, **update},
            event="hunt.triage",
            triaged_count=len(out),
        )
        return update

    return triage


def make_escalator(
    dispatch: HuntDispatch,
    threshold: int = DEFAULT_ESCALATION_THRESHOLD,
) -> Callable[[HuntState], dict]:
    def escalator(state: HuntState) -> dict:
        tasking = state["tasking"]
        tasking_id = str(tasking.tasking_id)
        triaged = state.get("triaged", [])

        escalatable = [
            t for t in triaged
            if t.triage in (Triage.CONFIRMED, Triage.SUSPICIOUS)
        ]
        case = None
        if len(escalatable) >= threshold:
            case = dispatch.open_case(tasking_id, escalatable)

        narrative = dispatch.narrate(tasking_id, triaged, case)

        report = HuntReport(
            tasking_id=tasking.tasking_id,
            hypotheses=state.get("hypotheses", []),
            queries=state.get("queries", []),
            hits=state.get("hits", []),
            triaged=triaged,
            case=case,
            narrative=narrative,
            tlp=tasking.tlp,
        )

        msg = AgentMessage(
            tasking_id=tasking.tasking_id,
            from_agent="hunt.escalator",
            to_agent=None,
            swarm="hunt",
            payload_type=PayloadType.REPORT,
            payload={
                "report_id": str(report.report_id),
                "case_opened": case is not None,
                "case_id": case.case_id if case else None,
                "hit_count": len(report.hits),
                "escalatable_count": len(escalatable),
            },
            markings=[tasking.tlp],
        )

        update = {
            "current_step": "escalator",
            "case": case,
            "narrative": narrative,
            "report": report,
            "messages": [msg],
            "done": True,
        }
        write_audit(
            {**state, **update},
            event="hunt.escalate",
            report_id=str(report.report_id),
            case_opened=case is not None,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        return update

    return escalator
