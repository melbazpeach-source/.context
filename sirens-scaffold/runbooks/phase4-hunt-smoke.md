# Runbook — Phase 4 Hunt-Swarm Smoke Test

**Owner:** Sirens ops
**Trigger:** Gate for Phase 4 kickoff exit.
**Severity at failure:** SEV3 (blocks Phase 4.1 — LiveDispatch wiring).
**Expected duration:** ~2 min automated + 15 min manual hand-trace.

---

## 0. What Phase 4 kickoff ships

The **scaffold** of the Hunt swarm. It contains:

- `schemas/hunt.py` — `Hypothesis`, `SigmaQuery`, `Hit`, `TriagedHit`,
  `HuntCase`, `HuntReport` + `HypothesisKind` / `Triage` enums.
- `agents/hunt/` — `HuntState`, five LangGraph nodes (hypothesis_planner
  → query_writer → hunter → triage → escalator), `HuntDispatch` Protocol,
  `StubDispatch` default impl, compiled graph. Conditional edge from
  `hypothesis_planner` short-circuits to `escalator` when no hypotheses
  apply (non-HUNT_TTP tasking).
- `agents/supervisor/subgraphs.py` now registers `"hunt"` alongside
  `"research"`. A `TaskingType.HUNT_TTP` tasking routes through the
  supervisor's `plan` → `dispatch` → **Hunt subgraph** → `finalize`.
- `tests/unit/test_hunt_golden_path.py` — 4 tests.
- One new supervisor-side test: `test_hunt_ttp_tasking_routes_to_hunt_swarm`.

What it does **not** yet ship (Phase 4.1):

- `LiveDispatch` wiring `plan_hypotheses` / `write_queries` /
  `execute_query` / `triage_hit` / `open_case` / `narrate` to real tools.
- pySigma backend adapters and SigmaHQ rule-pack loading.
- OTRF ThreatHunter-Playbook ingestion.
- Hunt policy in the scope allow-list (escalation threshold, auto-case
  severity, allowed index patterns).

Exit of this runbook means: the scaffold compiles, both graphs run, the
supervisor routes HUNT_TTP taskings correctly, and the contracts are
stable enough to build `LiveDispatch` against.

---

## 1. Automated tests

```bash
cd sirens
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/unit/ -v
```

Expected: 13 passing tests (3 research + 4 hunt + 6 supervisor).

Hunt-specific:

- `test_golden_path` — HUNT_TTP tasking with 2 targets → planner emits one
  IOC-sweep hypothesis per target; downstream stubs return empties;
  escalator emits a typed `HuntReport` with `case is None` and a REPORT
  `AgentMessage`.
- `test_non_hunt_tasking_short_circuits_to_escalator` — TRACK_ACTOR
  tasking → planner emits zero hypotheses → graph jumps straight to
  escalator → empty report.
- `test_escalator_opens_case_over_threshold` — custom `FakeDispatch` with
  2 hypotheses × 1 query × 3 hits × CONFIRMED triage = 6 escalatable
  hits ≥ threshold 3 → escalator calls `open_case` → `HuntCase` produced,
  message payload reports `case_opened=True`.
- `test_below_threshold_does_not_open_case` — 2 SUSPICIOUS hits < threshold
  3 → no case opened.

Supervisor-side:

- `test_hunt_ttp_tasking_routes_to_hunt_swarm` — HUNT_TTP tasking through
  `build_supervisor_graph(allowlist)` → two messages: STATUS
  `dispatched_to=hunt` + REPORT from `hunt.escalator`.

---

## 2. Hand-trace the scaffold

Prereqs: none beyond the venv from §1.

```bash
python - <<'PY'
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from agents.supervisor import build_supervisor_graph
from agents.supervisor.policy import (
    ApprovalRecord, Approvals, Collectors, EngagementMeta,
    ScopeAllowlist, TargetSet,
)
from schemas.tasking import Posture, Target, TargetKind, Tasking, TaskingType

now = datetime.now(timezone.utc)
al = ScopeAllowlist(
    allowlist_id="demo",
    engagement=EngagementMeta(
        customer="TestCo",
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=30),
    ),
    approvals=Approvals(legal=ApprovalRecord(
        approver="counsel@testco", approved_at=now,
    )),
    posture=Posture.PASSIVE_PUBLIC,
    targets=TargetSet(cves=["CVE-2026-0001"], malware_families=["Akira"]),
    collectors=Collectors(enabled=["wazuh"]),
)
t = Tasking(
    requester="demo@sirens",
    type=TaskingType.HUNT_TTP,
    targets=[
        Target(kind=TargetKind.CVE, value="CVE-2026-0001"),
        Target(kind=TargetKind.MALWARE_FAMILY, value="Akira"),
    ],
    posture=Posture.PASSIVE_PUBLIC,
)
result = build_supervisor_graph(al).invoke({"tasking": t, "run_id": uuid4()})
for m in result["messages"]:
    print(m.swarm, m.from_agent, m.payload_type.value)
PY
```

Expected:

```
supervisor supervisor.dispatch status
hunt       hunt.escalator      report
```

---

## 3. Contract review before Phase 4.1

Walk through `agents/hunt/dispatch.py` with whoever is writing the live
wiring. Per method:

| Method | Phase 4.1 wiring | Gotchas |
|---|---|---|
| `plan_hypotheses(tasking)` | OTRF ThreatHunter-Playbook + `Anthropic-Cybersecurity-Skills` mappings/mitre-attack/ + Claude | Skill drift — pin to a submodule SHA in CI. |
| `write_queries(hypothesis)` | SigmaHQ rule-pack (git clone) + `pysigma` + `pysigma-backend-opensearch` | Backend must match the log source; Wazuh's OpenSearch fork has ECS mapping quirks. |
| `execute_query(query)` | `mcp-server-wazuh` (vendored from gbrigandi) → OpenSearch `_search` | Enforce query time-window bounds; unbounded `_search` on hot indexes is the #1 cost footgun. |
| `triage_hit(hit)` | `sirens-mcp-opencti` (`search_entities`) + LLM classifier | Record OpenCTI anchor IDs in `TriagedHit.context` for audit. |
| `open_case(tasking_id, triaged)` | `mcp-server-thehive` (vendored) → `POST /api/v1/case` | Attach the tasking_id as a case tag; TheHive severity 1–4 not 1–5. |
| `narrate(...)` | Claude + `Anthropic-Cybersecurity-Skills` for ATT&CK tagging | Record token usage on `AgentMessage.audit` so the ledger-merge sees it. |

Every call goes through `x-tasking-id` — the MCP servers refuse calls
without it.

---

## 4. What else needs to land in 4.1

1. Escalation threshold should live in the scope allow-list
   (`hunt_policy.escalation_threshold`) not the build call.
2. ~~Sigma rule-pack as a git submodule.~~ Done — vendored at
   `sirens-scaffold/rules/sigma/` (SigmaHQ/sigma). LiveDispatch's
   `write_queries` will load YAML from there, translate via `pysigma` +
   `pysigma-backend-opensearch`, and emit `SigmaQuery` per candidate.
3. A Hunt-side integration test using a temp Wazuh indexer (ephemeral
   Docker) rather than stub — behind the `integration` marker.
4. Feedback loop: when the hunter returns zero hits but the Analyst
   believes the hypothesis is hot, enqueue a rule-gap ticket for the
   Detection-Engineering swarm (which doesn't exist yet — gap noted in
   `.context/research/sirens-swarm-survey.md §3.4`).

---

## 5. Exit criteria

- [ ] `pytest tests/unit/` green (13 tests)
- [ ] Hand-trace in §2 prints `supervisor.dispatch status` then
      `hunt.escalator report`
- [ ] `agents/hunt/dispatch.py:HuntDispatch` Protocol reviewed by whoever
      owns `LiveDispatch`; method signatures considered stable
- [ ] `HuntReport` + `HuntCase` schemas reviewed by whoever owns TheHive
      integration
- [ ] Escalation threshold's future home (allow-list vs build call) agreed
      before 4.1 starts

If any item fails, file an issue tagged `phase:4-kickoff blocker` and hold
Phase 4.1 (LiveDispatch wiring).
