"""Supervisor LangGraph nodes.

Each node takes SupervisorState and returns a partial update. Keep nodes
thin — move logic into policy/ and middleware/.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from agents.supervisor.middleware import (
    check_budget,
    check_ethics,
    check_scope,
    write_audit,
)
from agents.supervisor.policy import ScopeAllowlist
from agents.supervisor.state import SupervisorState, Violation, new_ledger
from schemas.agent_message import AgentMessage, PayloadType


def make_intake(allowlist: ScopeAllowlist):
    """Intake node: stamp run_id, init ledger, run policy gates."""

    def intake(state: SupervisorState) -> dict:
        run_id = state.get("run_id") or uuid4()
        ledger = new_ledger()

        base_update: dict = {
            "run_id": run_id,
            "ledger": ledger,
            "current_step": "intake",
        }

        violations: list[Violation] = []
        violations.extend(check_ethics(state))
        violations.extend(check_scope(state, allowlist))

        update = base_update | {"violations": violations}
        write_audit({**state, **update}, event="intake")

        if violations:
            update["done"] = True
            update["next_swarm"] = None
        return update

    return intake


def plan(state: SupervisorState) -> dict:
    """Decide which swarm to dispatch next.

    Phase 2 stub: map TaskingType → swarm. Phase 3+ replaces this with an
    LLM-generated plan composed of multiple AgentMessages.
    """
    from schemas.tasking import TaskingType

    type_to_swarm: dict[TaskingType, Literal["research", "hunt", "ir", "detection", "deception"]] = {
        TaskingType.TRACK_ACTOR: "research",
        TaskingType.WATCH_LEAK: "research",
        TaskingType.HUNT_TTP: "hunt",
        TaskingType.INGEST_REPORT: "research",
        TaskingType.ENRICH_OBSERVABLE: "research",
        TaskingType.AUTHOR_DETECTION: "detection",
        TaskingType.INVESTIGATE_INCIDENT: "ir",
        TaskingType.DEPLOY_DECEPTION: "deception",
    }

    next_swarm = type_to_swarm[state["tasking"].type]
    update = {"current_step": "plan", "next_swarm": next_swarm}
    write_audit({**state, **update}, event="plan", next_swarm=next_swarm)
    return update


def dispatch(state: SupervisorState) -> dict:
    """Deprecated — use make_dispatch(swarms). Kept for backwards compat."""
    return make_dispatch({})(state)


def make_dispatch(swarms: dict):
    """Factory that binds the swarm registry to the dispatch closure."""

    def dispatch(state: SupervisorState) -> dict:
        """Hand off to the selected swarm.

        Always emits a STATUS preamble (`dispatched_to=<swarm>`). If the swarm
        is registered in `swarms`, invoke the compiled subgraph and append its
        messages to the supervisor's message list. Otherwise STATUS-only — the
        swarm isn't built yet.
        """
        swarm = state["next_swarm"] or "research"
        out_messages = [
            AgentMessage(
                tasking_id=state["tasking"].tasking_id,
                from_agent="supervisor.dispatch",
                to_agent=None,
                swarm="supervisor",
                payload_type=PayloadType.STATUS,
                payload={"dispatched_to": swarm},
            )
        ]

        sub_app = swarms.get(swarm)
        if sub_app is not None:
            sub_result = sub_app.invoke(
                {
                    "tasking": state["tasking"],
                    "run_id": state.get("run_id"),
                }
            )
            out_messages.extend(sub_result.get("messages", []))

        update = {
            "current_step": "dispatch",
            "messages": out_messages,
        }
        write_audit(
            {**state, **update},
            event="dispatch",
            swarm=swarm,
            subgraph_invoked=sub_app is not None,
            sub_message_count=len(out_messages) - 1,
        )
        return update

    return dispatch


def finalize(state: SupervisorState) -> dict:
    """Seal the run — budget check, done flag, audit."""
    new_budget_violations = check_budget(state)
    update: dict = {
        "current_step": "finalize",
        "done": True,
    }
    if new_budget_violations:
        update["violations"] = new_budget_violations
    write_audit(
        {**state, **update},
        event="finalize",
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
    return update
