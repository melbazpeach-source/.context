# Sirens Compose

Compose stacks for local development and small-scale production.

| File | Brings up |
|---|---|
| `docker-compose.knowledge.yml` | OpenCTI, MISP, TheHive, Cortex + shared deps (Elasticsearch, Redis, RabbitMQ, MinIO, Cassandra, MariaDB) |
| `docker-compose.connectors.yml` | OpenCTI external-import connectors (MITRE, OTX, CISA KEV, URLhaus, MalwareBazaar, ThreatFox) |
| `docker-compose.mcp.yml` | MCP servers (IntelOwl + vendored wazuh/cortex/misp/thehive) |
| `bootstrap/` | Idempotent post-boot setup: Sirens marking taxonomy, MISP feed enable |

Full step-by-step lives in `../runbooks/knowledge-spine-boot.md` and the
Phase 1 exit test in `../runbooks/phase1-smoke-test.md`.

## Quick start (Phase 1 knowledge spine)

```bash
cp .env.example .env
# Edit .env — replace every CHANGE_ME before launch.
docker compose -f docker-compose.knowledge.yml up -d
docker compose -f docker-compose.knowledge.yml ps
```

URLs after first boot (~5 min):

| Service | URL | Login |
|---|---|---|
| OpenCTI | http://localhost:8080 | `admin@opencti.io` / `OPENCTI_ADMIN_PASSWORD` |
| MISP | https://localhost (self-signed TLS) | `admin@admin.test` / `MISP_ADMIN_PASSWORD` |
| TheHive | http://localhost:9000 | `admin@thehive.local` / `THEHIVE_ADMIN_PASSWORD` |
| Cortex | http://localhost:9001 | bootstrap on first visit |

## Sizing

Tested on 32 GB RAM / 8 vCPU / 500 GB NVMe. Elasticsearch heap
(`ES_JAVA_OPTS`) and Cassandra heap are the hottest knobs.

## Production hardening (not in scope here)

- TLS termination at a reverse proxy (Caddy / Traefik).
- Secrets in HashiCorp Vault / Doppler / 1Password Connect — never in `.env`.
- Nightly volume snapshots; tested restore.
- Elasticsearch + Cassandra in cluster mode across ≥3 nodes.
- Network segmentation: knowledge stack on a private subnet; only the
  supervisor host can reach it.
- Log shipping to a centralized SIEM (yes, including Sirens' own logs).
