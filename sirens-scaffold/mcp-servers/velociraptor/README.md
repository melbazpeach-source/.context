# sirens-mcp-velociraptor

MCP server wrapping [Velociraptor](https://docs.velociraptor.app/) over its
gRPC API (via `pyvelociraptor`).

## Tools

| Tool | Input | Output |
|---|---|---|
| `list_clients` | `search`, `limit` | `list[Client]` |
| `get_client` | `client_id` | `Client \| null` |
| `list_artifacts` | `search` (regex), `limit` | `list[Artifact]` |
| `collect_artifact` | `client_id`, `artifact`, `parameters`, `ttl_seconds` | `Flow` |
| `list_flows` | `client_id`, `limit` | `list[Flow]` |
| `get_flow` | `client_id`, `flow_id` | `Flow \| null` |
| `get_flow_results` | `client_id`, `flow_id`, `artifact`, `limit` | `list[dict]` |
| `run_vql` | `query`, `env`, `limit` | `list[dict]` |

All tools require `x-tasking-id`.

## Active-authorization gate

`run_vql` is unrestricted by design — it's the escape hatch for DFIR
operators. The MCP boundary therefore demands `x-active-authorization: true`
for that tool only. The supervisor sets that header only when the tasking
carries an Authorization record whose posture admits arbitrary operator
queries (typically `INVESTIGATE_INCIDENT`). All other tools work without
it because Velociraptor targets only customer-owned endpoints enumerated
in the scope allow-list; authorization is already proven at the scope
gate.

## Environment

| Var | Purpose |
|---|---|
| `VELOCIRAPTOR_CONFIG` | Path to `api.config.yaml` (default: `/etc/velociraptor/api.config.yaml`) |
| `VELOCIRAPTOR_TIMEOUT` | gRPC + VQL timeout seconds (default: `120`) |

The config file must contain client TLS certs for the API role — generate
with `velociraptor config api_client` on the Velociraptor server.

## Install & run (dev)

```bash
pip install -e .
export VELOCIRAPTOR_CONFIG=/etc/velociraptor/api.config.yaml
sirens-mcp-velociraptor
```

## Safety notes

- `collect_artifact` triggers on-endpoint execution. Start with low-cost
  artifacts (e.g. `Windows.Network.Netstat`, `Linux.Sys.UserList`) during
  smoke tests. Never use `Generic.Client.Info` cluster-wide for
  exploratory probing — that's what `list_clients` is for.
- `get_flow_results` can return huge result sets; always set `limit`.
- `run_vql` wraps the caller's query in an outer `LIMIT` to cap rows
  even when the query omits one.
