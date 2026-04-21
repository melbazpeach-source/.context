# Sirens — Build Scaffold (staging)

This directory is **staged in the `.context` repo for convenience only**. The
permanent home for Sirens is `melbazpeach-source/sirens`. Once that repo
exists, copy this directory's contents to the root of the new repo and remove
it from `.context`.

```
sirens-scaffold/
├── compose/        # docker-compose stacks (knowledge spine, dev)
├── agents/         # LangGraph agents, one folder per swarm
├── mcp-servers/    # MCP servers Sirens writes (IntelOwl, OpenCTI, etc.)
├── prompts/        # Reusable agent prompts
├── schemas/        # Pydantic v2 schemas (tasking, agent messages)
├── docs/           # Ethics/legal, scope allow-list template
├── tests/          # Unit + integration tests
└── runbooks/       # On-call, backup/restore, key rotation, legal-incident
```

## Where to look

| You want to… | Read |
|---|---|
| Understand the architecture | `.context/research/sirens-swarm-survey.md` |
| Follow the phased build | `.context/research/sirens-build-plan.md` |
| Check monthly cost | `.context/research/sirens-cost-analysis.md` |
| Stand up the knowledge spine (Phase 1) | `compose/README.md` |
| Wire a new agent | `schemas/README.md`, `agents/README.md` |
| Sign off on legal posture | `docs/ethics-and-legal.md`, `docs/scope-allowlist.template.yaml` |

## Status

Phase 0 scaffolding only. No agent code, no MCP servers, no live integrations.
Each subdirectory has a `README.md` describing what belongs there.
