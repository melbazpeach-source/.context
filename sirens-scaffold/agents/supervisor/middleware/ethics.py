"""Ethics / legal gate.

Runs on every tasking before it is planned. Codifies the hard MUST-NOTs
from docs/ethics-and-legal.md so they're enforceable at runtime, not just
at sign-off.
"""

from __future__ import annotations

from datetime import datetime, timezone

from agents.supervisor.state import SupervisorState, Violation
from schemas.tasking import Posture, TaskingType


# Posture → tasking-type whitelist. Anything outside this is a violation.
ALLOWED_BY_POSTURE: dict[Posture, set[TaskingType]] = {
    Posture.PASSIVE_PUBLIC: {
        TaskingType.TRACK_ACTOR,
        TaskingType.WATCH_LEAK,
        TaskingType.HUNT_TTP,
        TaskingType.INGEST_REPORT,
        TaskingType.ENRICH_OBSERVABLE,
        TaskingType.AUTHOR_DETECTION,
    },
    Posture.DECEPTION_INTERNAL: {
        TaskingType.DEPLOY_DECEPTION,
        TaskingType.INVESTIGATE_INCIDENT,
    },
    Posture.DECEPTION_AUTHORIZED: {
        TaskingType.DEPLOY_DECEPTION,
        TaskingType.INVESTIGATE_INCIDENT,
        TaskingType.TRACK_ACTOR,
    },
}


def check_ethics(state: SupervisorState) -> list[Violation]:
    tasking = state["tasking"]
    violations: list[Violation] = []
    now = datetime.now(timezone.utc)

    allowed = ALLOWED_BY_POSTURE.get(tasking.posture, set())
    if tasking.type not in allowed:
        violations.append(
            Violation(
                kind="ethics",
                detail=(
                    f"TaskingType {tasking.type.value!r} is not permitted "
                    f"under posture {tasking.posture.value!r}."
                ),
                raised_at=now,
            )
        )

    if tasking.posture is Posture.DECEPTION_AUTHORIZED and tasking.authorization is None:
        violations.append(
            Violation(
                kind="ethics",
                detail="DECEPTION_AUTHORIZED posture requires an Authorization record.",
                raised_at=now,
            )
        )

    if (
        tasking.authorization is not None
        and tasking.authorization.expires_at <= now
    ):
        violations.append(
            Violation(
                kind="ethics",
                detail="Authorization has expired.",
                raised_at=now,
            )
        )

    return violations
