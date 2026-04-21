# Sirens Agents

LangGraph agents. One subdirectory per swarm.

```
agents/
├── supervisor/        # Top-level router; budget, HITL, policy gates
├── research/          # OSINT collection, enrichment, correlation, reporting
├── hunt/              # Hypothesis-Generator, Query-Writer, Evaluator, Escalator
├── ir/                # Triage, Acquisition, Timeline-Builder, Scoper, Responder
├── detection/         # Sigma/YARA/Nuclei authoring + CTI-REALM reward loop
└── deception/         # Honey-token / honeypot / sinkhole controllers
```

Every agent:

- Accepts and emits `schemas/agent_message.AgentMessage`.
- Calls tools via MCP (no direct vendor SDK use).
- Logs every tool invocation into the `audit` block.
- Honors `markings` (TLP) and `requires_human_approval`.
- Refuses any action outside the active scope allow-list.

Skeleton lives here once Phase 2 begins. Phase 0 only ships this README.
