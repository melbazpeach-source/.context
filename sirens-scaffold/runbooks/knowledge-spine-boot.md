# Runbook — Knowledge Spine Boot

**Owner:** Sirens ops
**Trigger:** First-time build, or disaster-recovery rebuild.
**Severity at failure:** SEV3 during build, SEV2 if DR.
**Expected duration:** ~30 min first boot + ~60 min feed ingest.

---

## 0. Prerequisites

Host:

- Linux (Debian/Ubuntu 22.04+ tested)
- Docker Engine ≥ 24 and Docker Compose v2
- 32 GB RAM / 8 vCPU / 500 GB NVMe (dev); 64 GB / 16 / 1 TB (small prod)
- Outbound HTTPS to: `docker.elastic.co`, `ghcr.io`, `docker.io`,
  `otx.alienvault.com`, `urlhaus.abuse.ch`, `threatfox.abuse.ch`,
  `mb-api.abuse.ch`, `cisa.gov`, `github.com/mitre/cti`

Credentials already on file (see `docs/ethics-and-legal.md`):

- AlienVault OTX free account + API key
- Counsel sign-off on `docs/ethics-and-legal.md`

---

## 1. Prepare env files

```bash
cd sirens/compose
cp .env.example .env
cp .env.connectors.example .env.connectors
```

Fill in every `CHANGE_ME`:

- `OPENCTI_ADMIN_PASSWORD`, `OPENCTI_ADMIN_TOKEN` (UUIDv4)
- `ELASTIC_PASSWORD`, `REDIS_PASSWORD`, `RABBITMQ_DEFAULT_PASS`
- `MINIO_ROOT_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`
- `MISP_ADMIN_PASSWORD`, `MISP_ADMIN_KEY` (40-char alnum)
- `THEHIVE_ADMIN_PASSWORD`, `THEHIVE_SECRET`, `CORTEX_SECRET` (64-char random)
- All six `CONNECTOR_*_ID` UUIDs and `ALIENVAULT_API_KEY`

Generate UUIDs/secrets:

```bash
python3 -c "import uuid; [print(uuid.uuid4()) for _ in range(6)]"
openssl rand -hex 32   # 64-char hex for THEHIVE_SECRET, CORTEX_SECRET
openssl rand -hex 20   # 40-char for MISP_ADMIN_KEY
```

**Do not commit either .env file.** Both are in `.gitignore`.

---

## 2. Host sysctls (one-time)

Elasticsearch needs `vm.max_map_count` raised:

```bash
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee /etc/sysctl.d/99-sirens.conf
```

---

## 3. Bring up the knowledge stack

```bash
docker compose \
  --env-file .env \
  -f docker-compose.knowledge.yml \
  up -d
```

Wait for health. On first boot, OpenCTI spends ~5 min bootstrapping
Elasticsearch indexes and MinIO buckets before it opens its port.

```bash
# Poll until OpenCTI answers 200
until curl -fs http://localhost:8080/ > /dev/null; do
  echo "waiting for opencti..."; sleep 10
done

# MISP is slower (~8–10 min first run while it initializes the DB)
until curl -fsk https://localhost/users/login > /dev/null; do
  echo "waiting for misp..."; sleep 15
done

# TheHive last
until curl -fs http://localhost:9000/api/status > /dev/null; do
  echo "waiting for thehive..."; sleep 10
done
```

Verify in browser:

| URL | Login |
|---|---|
| http://localhost:8080 | `admin@opencti.io` / `OPENCTI_ADMIN_PASSWORD` |
| https://localhost | `admin@admin.test` / `MISP_ADMIN_PASSWORD` (accept self-signed cert) |
| http://localhost:9000 | first-run wizard |
| http://localhost:9001 | first-run wizard |

---

## 4. Bring up the feed connectors

```bash
docker compose \
  --env-file .env --env-file .env.connectors \
  -f docker-compose.knowledge.yml \
  -f docker-compose.connectors.yml \
  up -d
```

Initial imports run for 20–60 min each:

- **MITRE**: 3–5 min.
- **CISA KEV**: 1–2 min.
- **OTX** (from 2024-01-01): 30–90 min.
- **URLhaus / MalwareBazaar / ThreatFox**: 10–30 min.

Watch progress:

```bash
docker compose logs -f connector-mitre
docker compose logs -f connector-alienvault
```

OpenCTI UI → "Data" → "Ingestion" → "Connectors" shows each connector
heartbeating and its last run timestamp.

---

## 5. Bootstrap markings + MISP feeds

Once OpenCTI shows Status=green for all six connectors, run the bootstrap:

```bash
cd bootstrap
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Export values from ../.env
export OPENCTI_URL=http://localhost:8080
export OPENCTI_ADMIN_TOKEN=<from .env>
export MISP_URL=https://localhost
export MISP_ADMIN_KEY=<from .env>
export MISP_VERIFY_TLS=false   # dev only; TLS is self-signed

python opencti_markings.py
python misp_feeds.py
```

Expected output: 4 `CREATE` lines from the markings script (re-runs show
`SKIP`); 5 `ENABLE` lines from the MISP script (re-runs show `SKIP`). Any
`MISS` from the MISP script indicates a feed the MISP image did not seed
— open an issue before continuing.

---

## 6. TheHive → Cortex wiring

In TheHive UI:

1. Log in as the admin created in first-run wizard.
2. Organization → Integrations → Cortex → add server:
   - Name: `cortex-local`
   - URL: `http://cortex:9001`
   - API key: (Cortex UI → Organization → Users → create org admin → API key)
3. Test connection.

In Cortex UI:

1. Add MISP as an analyzer feed (Cortex → Organization → Analyzers → MISP).
   URL `https://misp`, key from `.env`.
2. Enable a minimal analyzer set: `Abuse_Finder`, `CyberCrime-Tracker`,
   `MISP_2_1`, `MalwareBazaar_GetInformation_1_0`, `VirusTotal_GetReport_3_1`
   (key optional).

---

## 7. Verification checklist

- [ ] OpenCTI: ≥ 20 ATT&CK techniques visible (`Knowledge → Arsenal → Attack patterns`)
- [ ] OpenCTI: ≥ 100 indicators from OTX (`Observations → Indicators`)
- [ ] OpenCTI: ≥ 10 CISA KEV vulnerabilities (`Arsenal → Vulnerabilities`)
- [ ] OpenCTI: four `SIRENS:*` marking-definitions visible (`Settings → Taxonomies → Marking Definitions`)
- [ ] MISP: 5 feeds enabled with non-zero event counts (`Sync Actions → List Feeds`)
- [ ] TheHive: Cortex connection status = healthy
- [ ] Cortex: `MISP_2_1` analyzer runs successfully on a test indicator

---

## 8. Known failure modes

| Symptom | Cause | Fix |
|---|---|---|
| OpenCTI HTTP 502 after 10 min | Elasticsearch OOM | Raise `ES_JAVA_OPTS` to `-Xms4g -Xmx4g`, recreate `elasticsearch` service |
| MISP loops on "Starting the application" | MariaDB init race | `docker compose restart mariadb misp`; wait 5 min; retry |
| TheHive refuses to start with Cassandra error | Cassandra still initializing | `docker compose logs cassandra` — wait for "Starting listening for CQL clients", then restart TheHive |
| Connector stuck `standby` | Bad `CONNECTOR_ID` (reused or invalid UUID) | Regenerate UUID in `.env.connectors`, `docker compose up -d` |
| OTX connector says "unauthorized" | Wrong `ALIENVAULT_API_KEY` | Re-copy from OTX settings page |

---

## 9. Backup first touch

Before ingesting any real data, snapshot the empty state so restore testing
has a baseline:

```bash
sudo tar czf /backups/sirens-knowledge-$(date +%F).tar.gz \
  /var/lib/docker/volumes/sirens-knowledge_*
```

See `backup-restore.md` (Phase 1 deliverable) for quarterly restore drills.

---

## Exit criteria (Phase 1)

All items in §7 checked, and `phase1-smoke-test.md` completes green.
