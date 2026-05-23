"""Scope allow-list gate.

Every target on the tasking must be enumerated in the allow-list and the
engagement window must be active. Restrictions always win over allows.
"""

from __future__ import annotations

from datetime import datetime, timezone

from agents.supervisor.policy import ScopeAllowlist
from agents.supervisor.state import SupervisorState, Violation


def check_scope(
    state: SupervisorState,
    allowlist: ScopeAllowlist,
) -> list[Violation]:
    tasking = state["tasking"]
    violations: list[Violation] = []
    now = datetime.now(timezone.utc)

    if not allowlist.window_active(now):
        violations.append(
            Violation(
                kind="scope",
                detail=(
                    f"Engagement window inactive "
                    f"({allowlist.engagement.starts_at.isoformat()} .. "
                    f"{allowlist.engagement.ends_at.isoformat()})."
                ),
                raised_at=now,
            )
        )

    if tasking.posture != allowlist.posture:
        violations.append(
            Violation(
                kind="scope",
                detail=(
                    f"Tasking posture {tasking.posture.value!r} does not match "
                    f"allow-list posture {allowlist.posture.value!r}."
                ),
                raised_at=now,
            )
        )

    for target in tasking.targets:
        if allowlist.forbids(target):
            violations.append(
                Violation(
                    kind="scope",
                    detail=f"Target {target.kind.value}:{target.value} is restricted.",
                    raised_at=now,
                )
            )
            continue
        if not allowlist.covers(target):
            violations.append(
                Violation(
                    kind="scope",
                    detail=f"Target {target.kind.value}:{target.value} not in allow-list.",
                    raised_at=now,
                )
            )

    return violations
