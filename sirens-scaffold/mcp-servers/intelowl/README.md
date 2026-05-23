# sirens-mcp-intelowl

MCP server wrapping [IntelOwl](https://github.com/intelowlproject/IntelOwl)
for Sirens agents.

## Tools

| Tool | Input | Output |
|---|---|---|
| `submit_observable` | `Observable`, optional `analyzers[]` or `playbook` | `SubmitResponse{job_id, status}` |
| `get_job` | `job_id` | `JobStatus{...}` |
| `list_analyzers` | — | `list[str]` |
| `list_playbooks` | — | `list[str]` |

All tools require an `x-tasking-id` header; calls without it are refused.

## Environment

| Var | Purpose |
|---|---|
| `INTELOWL_URL` | Base URL (default: `http://intelowl:80`) |
| `INTELOWL_TOKEN` | IntelOwl API token (required) |
| `INTELOWL_TIMEOUT` | HTTP timeout seconds (default: `30`) |

## Install & run (dev)

```bash
pip install -e .
export INTELOWL_URL=https://intelowl.local
export INTELOWL_TOKEN=your_token
sirens-mcp-intelowl          # stdio transport
```

Docker image is built in Phase 2 (`compose/docker-compose.mcp.yml`).

## Rate budget

One IntelOwl job = one `submit_observable` + N `get_job` polls. Agents
should prefer `playbook`-driven submissions over direct analyzer lists
when possible, to let IntelOwl batch and rate-limit internally.
