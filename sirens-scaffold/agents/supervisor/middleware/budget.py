"""Budget ceiling gate.

Checks the running ledger against the tasking's Budget. The ledger is
updated by the audit middleware on every AgentMessage ingestion.
"""

from __future__ import annotations

from datetime import datetime, timezone

from agents.supervisor.state import SupervisorState, Violation


def check_budget(state: SupervisorState) -> list[Violation]:
    tasking = state["tasking"]
    ledger = state.get("ledger")
    if ledger is None:
        return []

    violations: list[Violation] = []
    now = datetime.now(timezone.utc)
    b = tasking.budget

    if ledger["input_tokens"] > b.max_input_tokens:
        violations.append(
            Violation(
                kind="budget",
                detail=(
                    f"input_tokens {ledger['input_tokens']} > "
                    f"max_input_tokens {b.max_input_tokens}"
                ),
                raised_at=now,
            )
        )
    if ledger["output_tokens"] > b.max_output_tokens:
        violations.append(
            Violation(
                kind="budget",
                detail=(
                    f"output_tokens {ledger['output_tokens']} > "
                    f"max_output_tokens {b.max_output_tokens}"
                ),
                raised_at=now,
            )
        )
    if ledger["cost_usd"] > b.max_cost_usd:
        violations.append(
            Violation(
                kind="budget",
                detail=f"cost_usd {ledger['cost_usd']:.2f} > max_cost_usd {b.max_cost_usd}",
                raised_at=now,
            )
        )
    if b.deadline is not None and now > b.deadline:
        violations.append(
            Violation(
                kind="budget",
                detail=f"Deadline {b.deadline.isoformat()} passed.",
                raised_at=now,
            )
        )

    return violations
