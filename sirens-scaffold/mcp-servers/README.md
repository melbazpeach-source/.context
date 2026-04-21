# Sirens MCP Servers

The supervisor and every agent reach the world only through MCP. Existing
upstream MCP servers (Wazuh, Cortex, MISP, TheHive — all from `gbrigandi`)
are vendored as git submodules. New servers Sirens writes live here.

## To write (in build order)

| Server | Wraps | Phase |
|---|---|---|
| `intelowl/` | IntelOwl REST API | 2 |
| `opencti/` | OpenCTI GraphQL | 2 |
| `spiderfoot/` | SpiderFoot HX API | 3 |
| `velociraptor/` | Velociraptor API | 6 |
| `canarytokens/` | Canarytokens callbacks | 7 |

## Convention

Each server:

- Implements the standard MCP transport (`stdio` and `streamable-http`).
- Exposes a tool registry where every tool has: a JSON schema for input,
  a JSON schema for output, a stable name, a one-line description, and a
  cost-class tag (`free` / `paid:cheap` / `paid:expensive`).
- Emits OpenTelemetry spans tagged with `mcp.server`, `mcp.tool`,
  `tasking_id`, `cost_usd`.
- Refuses any call without a `tasking_id` header — the supervisor sets it.

## Upstream (no fork; vendored as submodules in Phase 2)

- `mcp-server-wazuh`   — https://github.com/gbrigandi/mcp-server-wazuh
- `mcp-server-cortex`  — https://github.com/gbrigandi/mcp-server-cortex
- `mcp-server-misp`    — https://github.com/gbrigandi/mcp-server-misp
- `mcp-server-thehive` — https://github.com/gbrigandi/mcp-server-thehive
