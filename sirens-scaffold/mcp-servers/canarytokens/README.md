# sirens-mcp-canarytokens

MCP server wrapping self-hosted [Canarytokens](https://github.com/thinkst/canarytokens)
(the `canarytokens-docker` stack).

## Tools

| Tool | Input | Output |
|---|---|---|
| `list_token_types` | — | `list[str]` |
| `create_token` | `CreateTokenInput` (type, memo, email?, webhook_url?, extra) | `Token` |
| `get_token_history` | `token`, `auth` | `list[TokenHit]` |
| `disable_token` | `token`, `auth` | `{token, status}` |

All tools require `x-tasking-id`.

## Webhook allow-list

`create_token` refuses any `webhook_url` whose host is not in
`CANARYTOKENS_ALLOWED_WEBHOOK_HOSTS`. This stops a compromised agent
from redirecting canary alerts to an attacker-owned endpoint. The
supervisor normally injects the Sirens audit sink as the webhook, so
that allow-list should contain only that host.

Default behavior: if the env var is empty, **all webhooks are rejected**
(fail-closed). Email-only alerting still works.

## Environment

| Var | Purpose |
|---|---|
| `CANARYTOKENS_URL` | Base URL (default: `http://canarytokens:8080`) |
| `CANARYTOKENS_TIMEOUT` | HTTP timeout seconds (default: `30`) |
| `CANARYTOKENS_ALLOWED_WEBHOOK_HOSTS` | Comma-separated host allow-list for `webhook_url` |

## Install & run (dev)

```bash
pip install -e .
export CANARYTOKENS_URL=http://localhost:8080
export CANARYTOKENS_ALLOWED_WEBHOOK_HOSTS=audit.sirens.internal
sirens-mcp-canarytokens
```

## Deployment model

Canarytokens are a DECEPTION_INTERNAL capability by default: placed on
customer-owned infra to alert on unauthorized access. Placement targets
must appear in the scope allow-list's `active_capabilities.honey_tokens`
list with an authorization record. The supervisor refuses to call
`create_token` for any other case.

## Noise budget

Each deployed token emits on every trigger. Design pattern:

- One memo per deployment location (host, share, bucket) so hits are
  attributable.
- Budget ~10 active tokens per customer to start; bump only after the
  noise profile is understood.
- On a triggered alert, the Deception swarm should correlate against
  IR / Hunt contexts before notifying SOC — don't page on first hit.
