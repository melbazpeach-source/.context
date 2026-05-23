# Supervisor

Top-level LangGraph router. Accepts a `Tasking`, enforces policy, dispatches
to a downstream swarm (Phase 3+), and audits every transition.

## Graph

```
       ┌─────────┐
       │ intake  │   init ledger, ethics + scope gates
       └────┬────┘
     violations?
        ┌───┴───┐
       no      yes
        │       │
        ▼       │
    ┌──────┐   │
    │ plan │   │
    └──┬───┘   │
       │       │
       ▼       │
  ┌──────────┐ │
  │ dispatch │ │
  └────┬─────┘ │
       │       │
       ▼       ▼
     ┌──────────┐
     │ finalize │   budget check, audit, done=True
     └──────────┘
```

## Middleware (all run on every transition)

| Gate | Enforces | On failure |
|---|---|---|
| `ethics` | `docs/ethics-and-legal.md` posture matrix, authorization validity | Skip plan/dispatch; finalize with `ethics` violations |
| `scope` | Per-engagement allow-list (targets, window, restrictions) | Same — recorded as `scope` violations |
| `budget` | Per-tasking `Budget` (tokens, cost, deadline) | Recorded as `budget` violations at finalize |
| `rate_limit` | In-process token-bucket per tool/collector key | Returns violation; caller retries or re-routes |
| `audit` | Writes every state transition | Best-effort; never breaks flow |

## Running

```python
from pathlib import Path

from agents.supervisor import build_supervisor_graph
from agents.supervisor.policy import load_allowlist
from schemas.tasking import Tasking

allowlist = load_allowlist(Path("docs/engagements/acme-q2-2026.yaml"))
app = build_supervisor_graph(allowlist)

tasking = Tasking.model_validate_json(open("tasking.json").read())
result = app.invoke({"tasking": tasking})
```

`result` contains final `messages`, `violations`, `ledger`, and `done=True`.

## Tests

See `tests/unit/test_supervisor_golden_path.py` for the end-to-end contract
test required to exit Phase 2.

## Not yet implemented (Phase 3+)

- Real swarm dispatch — `dispatch()` currently only emits a STATUS message.
- LLM-driven `plan()` that composes multiple AgentMessages instead of a
  one-shot type→swarm map.
- HITL gate on `requires_human_approval` messages.
- Distributed rate limiter (Redis).
- Persistent audit sink (Postgres / object storage).
