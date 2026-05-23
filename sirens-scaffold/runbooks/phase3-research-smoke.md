# Runbook — Phase 3 Research-Swarm Smoke Test

**Owner:** Sirens ops
**Trigger:** Gate for Phase 3 kickoff exit.
**Severity at failure:** SEV3 (blocks Phase 3.1 — LiveDispatch wiring).
**Expected duration:** ~2 min automated + 20 min manual hand-trace.

---

## 0. What Phase 3 kickoff ships

This is the **scaffold** of the Research swarm. It contains:

- `schemas/research.py` — `ResearchQuery`, `Observable`, `EnrichedObservable`,
  `Campaign`, `DraftDetection`, `ResearchReport`.
- `agents/research/` — `ResearchState`, six LangGraph nodes
  (planner → collector → enricher → correlator → analyst → reporter),
  `ResearchDispatch` Protocol, `StubDispatch` default impl, compiled graph.
- `tests/unit/test_research_golden_path.py` — 3 tests.

What it does **not** yet ship (Phase 3.1):

- `LiveDispatch` wiring `collect` / `enrich` / `correlate` / `narrate` /
  `build_stix_bundle` to actual MCP brokers and LLM calls.
- Supervisor → Research subgraph integration (`dispatch` node still just
  emits a STATUS message).
- Detection-Engineering feedback loop (drafts arrive in `ResearchReport`
  but are not yet consumed).

Exit of this runbook means: the scaffold compiles, the graph runs, and the
contracts are stable enough to build `LiveDispatch` against.

---

## 1. Automated golden-path tests

```bash
cd sirens
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/unit/test_research_golden_path.py -v
```

Expected: 3 passing tests.

- `test_golden_path` — INGEST_REPORT tasking with 3 heterogeneous targets →
  planner emits ≥1 query per target kind, graph advances through every
  node, reporter emits a typed `ResearchReport` with a shape-valid STIX
  bundle and a REPORT `AgentMessage`.
- `test_planner_skips_reporter_when_no_queries_match` — ASN target under
  WATCH_LEAK → planner emits zero queries → conditional edge short-circuits
  to reporter, which still produces a typed report (narrative synthesised
  via dispatch.narrate as a fallback).
- `test_reporter_integrates_dispatch_outputs` — custom `FakeDispatch`
  returning one synthetic Observable per query → observable count equals
  query count, verdicts propagate to the report, narrative interpolates
  the tasking id.

---

## 2. Hand-trace the scaffold

Prereqs: none beyond the venv from §1.

```bash
python - <<'PY'
from datetime import datetime, timezone
from uuid import uuid4
from agents.research import build_research_graph
from schemas.tasking import Posture, Target, TargetKind, Tasking, TaskingType

t = Tasking(
    requester="you@sirens",
    type=TaskingType.TRACK_ACTOR,
    targets=[
        Target(kind=TargetKind.ACTOR, value="Scattered Spider"),
        Target(kind=TargetKind.DOMAIN, value="bad-actor-infra.test"),
    ],
    posture=Posture.PASSIVE_PUBLIC,
)
app = build_research_graph()
result = app.invoke({"tasking": t, "run_id": uuid4()})

print("queries:   ", len(result.get("queries", [])))
print("observables:", len(result.get("observables", [])))
print("enriched:  ", len(result.get("enriched", [])))
print("done:      ", result.get("done"))
print("narrative: ", result["report"].narrative)
PY
```

Expected:

- `queries` ≥ 1 (TRACK_ACTOR × 2 targets across 6 query kinds, filtered to
  the kinds each target kind is accepted by).
- `observables` / `enriched` = 0 (StubDispatch returns empty lists).
- `done` is True.
- `narrative` is the stub line naming the tasking id and zero observables.

---

## 3. Contract review before Phase 3.1

Walk through `agents/research/dispatch.py` with whoever is writing
`LiveDispatch`. For each method, confirm:

| Method | Phase 3.1 wiring | Gotchas |
|---|---|---|
| `collect(query)` | `sirens-mcp-spiderfoot`, direct REST for abuse.ch, OTX, Shodan, Censys, GreyNoise, VT, GitGuardian, Ahmia | Per-source rate-limit inside dispatch, not per-call. De-dupe observables across sources before returning. |
| `enrich(observable)` | `sirens-mcp-intelowl` (`submit_observable` → poll `get_job`) | Budget gate — IntelOwl fan-out is the heaviest spend step. |
| `correlate(tasking_id, enriched)` | `sirens-mcp-opencti` (`search_entities`, `add_relationship`, `create_report`) | pycti filter shape is version-pinned; see `mcp-servers/opencti/README.md`. |
| `narrate(tasking_id, campaign, enriched)` | Claude (`anthropic` SDK) with Anthropic-Cybersecurity-Skills for ATT&CK tagging | Record token usage in `AgentMessage.audit`; skill scaffolds are the source of truth for technique IDs. |
| `build_stix_bundle(...)` | `stix2` library + `sirens-mcp-opencti.create_report` | Emit TLP marking object matching `tasking.tlp`. |

Every `LiveDispatch` call must set the `x-tasking-id` header on the MCP
call — the MCP servers refuse calls without it.

---

## 4. Supervisor hand-off (wired)

The supervisor's `dispatch` node now invokes the Research subgraph when
`next_swarm == "research"`. Implementation lives in:

- `agents/supervisor/subgraphs.py` — `SwarmRegistry` = `dict[str, Any]`;
  `build_default_swarms(research_dispatch)` wires Research with
  `StubDispatch` by default, or a `LiveDispatch` passed in by the caller.
- `agents/supervisor/nodes.py` — `make_dispatch(swarms)` is a factory; the
  inner closure always emits a STATUS preamble, then invokes
  `swarms[next_swarm]` if registered and appends its messages.
- `agents/supervisor/graph.py` — `build_supervisor_graph(allowlist,
  swarms=None)` takes an optional registry so callers can inject live-wired
  subgraphs.

End-to-end smoke (no infra, no API keys):

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
    targets=TargetSet(actors=["Scattered Spider"]),
    collectors=Collectors(enabled=["shodan"]),
)
t = Tasking(
    requester="demo@sirens",
    type=TaskingType.TRACK_ACTOR,
    targets=[Target(kind=TargetKind.ACTOR, value="Scattered Spider")],
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
research   research.reporter   report
```

Subgraph audit totals now fold into the supervisor's `BudgetLedger`
automatically. `dispatch` sums `AgentMessage.audit.{input_tokens,
output_tokens, cost_usd, tool_calls}` across every message the subgraph
returned and writes the updated ledger into state. `finalize`'s existing
`check_budget` then sees the merged totals.

Remaining for Phase 3.1:

1. Build `LiveDispatch(ResearchDispatch)` that binds MCP clients (IntelOwl,
   OpenCTI, SpiderFoot, Canarytokens, Velociraptor) + a Claude client for
   `narrate` + the `stix2` builder for `build_stix_bundle`.
2. Pass it through:
   `build_supervisor_graph(allowlist, swarms=build_default_swarms(live))`.
3. Ensure every LiveDispatch tool call records accurate `Audit.input_tokens
   / output_tokens / cost_usd / tool_calls` on the AgentMessage it produces
   — the budget gate is only as good as the audit blocks the swarm emits.

---

## 5. Exit criteria

- [ ] `pytest tests/unit/test_research_golden_path.py` green
- [ ] Hand-trace in §2 prints expected counts and narrative
- [ ] `agents/research/dispatch.py:ResearchDispatch` Protocol reviewed by
      whoever owns `LiveDispatch`; method signatures considered stable
- [ ] `ResearchReport` schema reviewed by whoever owns MISP + TheHive
      integration (fields for `misp_event_json` and `thehive_case_ref`
      are typed placeholders ready to populate)
- [ ] Supervisor `dispatch` node still emits STATUS only — integration is
      explicitly out of scope for the kickoff; that's expected

If any item fails, file an issue tagged `phase:3-kickoff blocker` and hold
Phase 3.1 (LiveDispatch wiring).
