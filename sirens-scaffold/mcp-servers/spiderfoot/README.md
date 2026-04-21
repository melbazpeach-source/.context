# sirens-mcp-spiderfoot

MCP server wrapping [SpiderFoot (OSS)](https://github.com/smicallef/spiderfoot).

## Tools

| Tool | Input | Output |
|---|---|---|
| `list_modules` | — | `list[Module]` |
| `list_event_types` | — | `list[str]` |
| `start_scan` | `target`, `name`, `usecase` (default Passive), `modules[]`, `event_types[]` | `Scan` |
| `get_scan` | `scan_id` | `Scan` |
| `list_scans` | `status_filter`, `limit` | `list[Scan]` |
| `get_scan_results` | `scan_id`, `event_type`, `limit` | `list[ScanResult]` |
| `get_scan_summary` | `scan_id` | `list[ScanSummary]` |
| `stop_scan` | `scan_id` | `{id, status}` |

All tools require `x-tasking-id`.

## Ethical default

`start_scan` runs with `usecase=Passive` unless the caller sets header
`x-active-authorization: true`. The supervisor may only set that header
when the tasking carries a valid `Authorization` record with a posture
that admits active reconnaissance. This enforces
`docs/ethics-and-legal.md` §Authorization matrix at the tool boundary.

## Environment

| Var | Purpose |
|---|---|
| `SPIDERFOOT_URL` | Base URL (default: `http://spiderfoot:5001`) |
| `SPIDERFOOT_USER` | Basic-auth user (optional) |
| `SPIDERFOOT_PASSWORD` | Basic-auth password (optional) |
| `SPIDERFOOT_TIMEOUT` | HTTP timeout seconds (default: `60`) |

## Install & run (dev)

```bash
pip install -e .
export SPIDERFOOT_URL=http://localhost:5001
sirens-mcp-spiderfoot
```

## Notes

- Targets SpiderFoot OSS ≥ 4.0 (JSON responses). The older HTML-forms
  API is not supported.
- `start_scan` returns the scan in its initial state; poll `get_scan`
  or `get_scan_summary` to observe progress.
- Prefer `get_scan_summary` over `get_scan_results` first — full result
  sets can be large.
