# Research swarm

The online-OSINT arm of Sirens: given a `Tasking`, produce a `ResearchReport`
(narrative + enriched observables + campaign graph + STIX bundle + draft
detections).

## Graph

```
planner ──(queries?)──▶ reporter  (empty report, zero observables)
   │
   └──▶ collector ─▶ enricher ─▶ correlator ─▶ analyst ─▶ reporter
```

Every node returns a partial `ResearchState` update. Lists are concatenated
via the `_append` reducer; scalars overwrite.

## Dispatch contract

Nodes reach the outside world through `ResearchDispatch` (a Protocol):

| Method | Wired to (Phase 3.1) |
|---|---|
| `collect(query)` | `sirens-mcp-spiderfoot`, direct abuse.ch / Shodan / Censys / OTX / GitGuardian / Ahmia clients |
| `enrich(observable)` | `sirens-mcp-intelowl` (`submit_observable` + poll `get_job`) |
| `correlate(tasking_id, enriched)` | `sirens-mcp-opencti` (`search_entities`, `add_relationship`) |
| `narrate(tasking_id, campaign, enriched)` | Claude (via Anthropic-Cybersecurity-Skills for ATT&CK tagging) |
| `build_stix_bundle(...)` | `stix2` library + `sirens-mcp-opencti.create_report` |

`StubDispatch` is the default used in unit tests and demos — it returns
shape-correct empty results so the graph is exercisable without the stack.

## Running the graph

```python
from agents.research import build_research_graph

app = build_research_graph()                    # StubDispatch default
result = app.invoke({"tasking": some_tasking, "run_id": uuid4()})

assert result["done"]
print(result["report"].narrative)
```

## Integration with the supervisor

Wired. `agents/supervisor/subgraphs.py` registers the Research graph under
`"research"`. When the supervisor's `dispatch` node sees `next_swarm ==
"research"`, it:

1. Emits a STATUS preamble (`dispatched_to=research`).
2. Invokes the Research subgraph with the Tasking and `run_id`.
3. Appends the subgraph's messages (including the REPORT) onto the
   supervisor's message list.

Callers wire a `LiveDispatch` by passing a custom registry:

```python
from agents.supervisor import build_supervisor_graph
from agents.supervisor.subgraphs import build_default_swarms

app = build_supervisor_graph(
    allowlist,
    swarms=build_default_swarms(research_dispatch=my_live_dispatch),
)
```

Still deferred to Phase 3.1: merging subgraph token / cost attribution back
onto the supervisor's `BudgetLedger` before `finalize` runs.

## What's not built yet (tickets for Phase 3.1+)

- `LiveDispatch` wiring every method to its MCP broker / API client.
- LLM-driven planner (currently rule-based mapping from TaskingType → QueryKind).
- Dedup across collectors (same hash from VT + abuse.ch → one Observable).
- Per-source rate-limit inside the collector.
- Draft-detection generation inside the Analyst (Sigma/YARA/Nuclei).
- Reporter writes to MISP + opens TheHive case on HITL approval.
- Detection-Engineering swarm consumes `draft_detections` once the swarm
  exists.
