# Sirens Schemas

Pydantic v2 models for the contracts that cross agent and swarm boundaries.

| File | Defines |
|---|---|
| `tasking.py` | `Tasking` — what enters the supervisor (a unit of work). |
| `agent_message.py` | `AgentMessage` — how agents speak to each other and to the supervisor. |

## Why schemas first

The Plan plays out in LangGraph nodes that pass JSON between each other. Locking
the contracts down before the agents are written keeps Phase 2 / 3 independent
and lets us swap LLM backends without breaking the wire.

## Versioning

Schemas are SemVer'd via the `schema_version` field. Breaking changes (renamed
or removed required fields) bump major; additive changes bump minor.

## Validation

```python
from schemas.tasking import Tasking
from schemas.agent_message import AgentMessage

t = Tasking.model_validate_json(open("examples/tasking.json").read())
m = AgentMessage.model_validate_json(payload)
```
