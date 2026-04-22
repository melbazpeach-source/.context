# Hunt swarm

The SIEM-side detection arm of Sirens: given a `HUNT_TTP` Tasking, form
hypotheses, translate them to Sigma queries, run the queries against the
log indexer, triage hits against OpenCTI context, and open a TheHive case
when enough confirmed/suspicious hits land.

## Graph

```
hypothesis_planner ──(no hypotheses?)──▶ escalator  (empty report)
   │
   └──▶ query_writer ─▶ hunter ─▶ triage ─▶ escalator
```

Every node returns a partial `HuntState` update. Lists concat via `_append`;
scalars overwrite.

## Dispatch contract

Nodes reach the outside world through `HuntDispatch` (a Protocol):

| Method | Wired to (Phase 4.1) |
|---|---|
| `plan_hypotheses(tasking)` | OTRF ThreatHunter-Playbook + ATT&CK skills via `anthropic-cybersecurity-skills`; Claude drafts hypotheses |
| `write_queries(hypothesis)` | SigmaHQ rule-pack lookup + `pysigma` + `pysigma-backend-opensearch` (in-process) |
| `execute_query(query)` | `mcp-server-wazuh` (vendored) → OpenSearch `_search` |
| `triage_hit(hit)` | `sirens-mcp-opencti` (`search_entities`) + LLM classifier |
| `open_case(tasking_id, triaged)` | `mcp-server-thehive` (vendored) → `POST /api/v1/case` |
| `narrate(...)` | Claude (via Anthropic-Cybersecurity-Skills) |

`StubDispatch` is the default for unit tests: it emits one IOC-sweep
hypothesis per target (for `HUNT_TTP` taskings), returns empty lists for
queries/hits, and classifies any hit as `BENIGN`.

## Escalation threshold

`build_hunt_graph(dispatch, escalation_threshold=N)` — default 3. Case is
opened only if the count of `CONFIRMED` + `SUSPICIOUS` triaged hits is ≥ N.
Tune this per engagement in the scope allow-list once allow-list gains a
hunt-policy block (not today).

## Running the graph

```python
from agents.hunt import build_hunt_graph

app = build_hunt_graph()                     # StubDispatch default
result = app.invoke({"tasking": some_tasking, "run_id": uuid4()})

assert result["done"]
print(result["report"].narrative)
```

## Integration with the supervisor

Registered in `agents/supervisor/subgraphs.py` under `"hunt"`. When the
supervisor's `plan` node maps `TaskingType.HUNT_TTP → "hunt"`, the
`dispatch` node invokes this subgraph and folds its audit totals into the
supervisor ledger.

## What's not built yet (tickets for Phase 4.1+)

- `LiveDispatch` wiring each method to its MCP broker / API client.
- pySigma backend selection per log source (opensearch-wazuh vs splunk
  vs sentinel).
- OTRF ThreatHunter-Playbook ingestion as a skill source.
- Per-hypothesis rule de-duplication and rate-limit.
- HITL approval before `open_case` when confidence is mid-band.
- Feedback loop to Detection-Engineering when a hypothesis is hot but no
  existing Sigma rule matched.
