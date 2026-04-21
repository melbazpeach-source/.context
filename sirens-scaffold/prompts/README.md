# Sirens Prompts

Reusable prompts for each agent. Versioned alongside the schemas they
reference; bump the prompt's `version` header when behavior changes.

Planned set (created in Phase 3 for Research, Phase 5 for Detection, etc.):

| Prompt | Used by |
|---|---|
| `planner.md` | Research / Planner |
| `collector.md` | Research / Collector base |
| `enricher.md` | Research / Enricher |
| `correlator.md` | Research / Correlator |
| `analyst.md` | Research / Analyst |
| `reporter.md` | Research / Reporter |
| `hypothesis-generator.md` | Hunt |
| `detection-writer.md` | Detection Engineering |
| `ir-triage.md` | IR / Triage |
| `deception-controller.md` | Deception |
| `supervisor-policy.md` | Supervisor (legal/ethics gate) |

## Header convention

Every prompt starts with a YAML front-matter block:

```yaml
---
name: planner
version: 0.1.0
inputs:
  - tasking: schemas/tasking.py:Tasking
outputs:
  - plan: list[AgentMessage]
model_class: opus | sonnet | haiku
hitl: false
---
```
