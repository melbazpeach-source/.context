# sirens-mcp-opencti

MCP server wrapping [OpenCTI](https://github.com/OpenCTI-Platform/opencti)
via the official `pycti` client.

## Tools

| Tool | Input | Output |
|---|---|---|
| `search_entities` | `query`, `entity_types[]`, `limit` | `list[EntitySummary]` |
| `get_entity` | `entity_id` | `EntitySummary \| null` |
| `list_reports` | `search`, `limit` | `list[Report]` |
| `create_indicator` | `CreateIndicatorInput` | `EntitySummary` |
| `create_report` | `CreateReportInput` (incl. `object_refs`) | `Report` |
| `add_relationship` | `RelationshipInput` | `{id, standard_id}` |

All tools require an `x-tasking-id` header. Every write is tagged with a
label `sirens:tasking:<id>` so provenance and clean-up are tractable.

## Environment

| Var | Purpose |
|---|---|
| `OPENCTI_URL` | Base URL (default: `http://opencti:8080`) |
| `OPENCTI_TOKEN` | OpenCTI API token (required) |
| `OPENCTI_SSL_VERIFY` | `true`/`false` (default: `true`) |

## Install & run (dev)

```bash
pip install -e .
export OPENCTI_URL=http://localhost:8080
export OPENCTI_TOKEN=<admin-or-service-token>
sirens-mcp-opencti
```

## Version pin

`pycti` is pinned to the platform version (currently `6.4.6`). Bump in
lock-step with the `opencti/platform` image tag in
`compose/docker-compose.knowledge.yml`.

## Write guardrails

- Writes are idempotent (`update=True`) — same `name + pattern` does not
  create a duplicate.
- `_tag()` failures do not roll back the write; the entity exists even if
  the tasking label couldn't be attached. Monitor audit logs for
  `tag_failed`.
- `add_relationship` does not create entities — both `from_id` and
  `to_id` must already exist.
