# Knowledge Spine Bootstrap

Idempotent setup that runs **once** after the compose stack is healthy:

1. Define Sirens marking-definition taxonomy in OpenCTI.
2. Enable default MISP feeds (CIRCL OSINT, abuse.ch, Botvrij).

## Usage

```bash
cd compose/bootstrap
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Populate from the same .env your compose uses
export OPENCTI_URL=http://localhost:8080
export OPENCTI_ADMIN_TOKEN=<from .env>
export MISP_URL=https://localhost
export MISP_ADMIN_KEY=<from .env>

python opencti_markings.py
python misp_feeds.py
```

Both scripts are safe to re-run — they check for existing state before
creating.

## What gets created

**OpenCTI marking-definitions:**

| Definition | Color | Purpose |
|---|---|---|
| `SIRENS:INTERNAL` | #666666 | Never leaves Sirens. Used for hypothesis / draft state. |
| `SIRENS:CUSTOMER_PRIVATE` | #cc0000 | Visible only to the customer who scoped the engagement. |
| `SIRENS:ATTRIBUTION_DRAFT` | #ff8800 | AI-proposed attribution, not yet human-validated. |
| `SIRENS:ATTRIBUTION_VALIDATED` | #00994c | Human-validated attribution. OK to include in customer-facing reports. |

Standard TLP markings (`TLP:CLEAR / GREEN / AMBER / AMBER+STRICT / RED`) are
already shipped by OpenCTI; the script verifies they exist and errors loudly
if not.

**MISP feeds enabled:**

| Feed | Source |
|---|---|
| CIRCL OSINT Feed | https://www.circl.lu/doc/misp/feed-osint/ |
| The Botvrij.eu Data | https://www.botvrij.eu/data/feed-osint/ |
| abuse.ch SSL IPBL | https://sslbl.abuse.ch/blacklist/sslipblacklist.csv |
| abuse.ch URLhaus | https://urlhaus.abuse.ch/downloads/csv_recent/ |
| abuse.ch Feodo Tracker | https://feodotracker.abuse.ch/downloads/ipblocklist.csv |
