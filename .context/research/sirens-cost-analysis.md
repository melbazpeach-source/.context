# Sirens — One-Page Monthly Cost Analysis

> **Basis:** running Sirens continuously, single-tenant, moderate tasking (~20 active investigations / month, 50 M input + 10 M output LLM tokens / month). Prices in USD as of early 2026; rounded.

---

## Scenario A — Free-Tier Only (self-hosted + free API tiers)

| Line item | Monthly |
|---|---|
| Dedicated host (32 GB / 8 vCPU / 500 GB NVMe — Hetzner AX-series or equivalent) | $100 |
| Secondary host (Wazuh indexer, 16 GB / 4 vCPU / 200 GB) | $50 |
| Bandwidth / egress | $20 |
| Domains, TLS, sinkhole authority DNS | $20 |
| Object storage (backups, pcap, sample archive; ~1 TB) | $25 |
| **Infrastructure subtotal** | **$215** |
| LLM inference — supervisor + analyst on Claude Opus 4.7, routine agents on Sonnet 4.6 | $650–$1,800 |
| **LLM subtotal** | **~$1,200 (midpoint)** |
| Free API tiers (abuse.ch suite, AlienVault OTX, NVD, CISA KEV, VulnCheck community, VirusTotal public, Shodan free, Censys free, GreyNoise community, GitHub API, Ahmia, nuclei-templates, PoC-in-GitHub, Canarytokens hosted-free) | $0 |
| Observability (self-hosted Prometheus/Grafana/Loki) | $0 |
| TheHive + Cortex + MISP + OpenCTI + IntelOwl + Wazuh (all OSS, self-hosted) | $0 |
| **TOTAL (Scenario A)** | **≈ $1,400 / month** |

**What you get:** complete swarm, all layers functional, research arm covering public OSINT, deception stack live on owned infra, detection drafts, HITL cases. No commercial feeds, no paid passive DNS.

**What you miss:** historic passive DNS, VirusTotal intelligence search, commercial dark-web monitoring, rich Shodan queries, RF/Mandiant/Intel471 finished-intel reports, adversary-infra attribution depth.

---

## Scenario B — With Essential Paid Tools

Adds the smallest paid stack that materially lifts capability without enterprise pricing.

| Additional line item | Monthly |
|---|---|
| **Shodan Membership / Small Business** (real queries, filters, monitor) | $70–$360 |
| **Censys Pro** | $500 |
| **VirusTotal Premium (VT Intelligence) — smallest seat** | $1,500 |
| **GreyNoise paid tier** | $200 |
| **Hybrid Analysis commercial** | $300 |
| **Triage Public+** | $500 |
| **DomainTools Iris Investigate — entry seat** | $850 |
| **Paid subtotal** | **≈ $4,100** |
| Scenario A baseline | $1,400 |
| **TOTAL (Scenario B)** | **≈ $5,500 / month** |

**What this unlocks:** historic passive DNS pivots, deep VT search (imphash / pe-debug / YARA livehunt), paid Shodan facets, registrar/WHOIS history, commercial sandbox detonations, richer GreyNoise classifiers.

---

## Scenario C — Enterprise Stack (reference only)

Not recommended for v0.1 — listed so the delta is visible.

| Additional line item | Monthly |
|---|---|
| Recorded Future | ~$2,500 |
| Mandiant Advantage | ~$3,500 |
| Intel 471 | ~$4,000 |
| Flashpoint | ~$4,000 |
| DarkOwl Vision | ~$2,000 |
| Farsight DNSDB full | ~$850 |
| Enterprise LLM contract (committed Opus 4.7 throughput) | +$2,000 |
| Larger infra (HA OpenCTI + MISP, sharded Wazuh) | +$1,000 |
| **Enterprise add-on subtotal** | **≈ $20,000** |
| **TOTAL (Scenario C)** | **≈ $25,000–$30,000 / month** |

---

## LLM Cost Sensitivity (biggest lever in A & B)

Assumes current Anthropic list prices.

| Strategy | Monthly LLM cost |
|---|---|
| All Opus 4.7 | $3,500–$5,000 |
| Supervisor + Analyst on Opus; Collector/Enricher/Reporter on Sonnet 4.6 (recommended) | $1,000–$1,500 |
| As above, with Haiku 4.5 for deterministic sub-tasks (summarisation, tagging, parsing) | $600–$1,000 |
| Aggressive prompt-caching on shared Substrate docs + MITRE scaffolds | –30 % on above |

**Recommendation:** Tiered routing + prompt caching. Budget **$1,000 / month for LLM** at v0.1 scale, supervisor-capped.

---

## Bottom Line

| Scenario | Monthly | Buys you |
|---|---|---|
| **A — Free-tier** | **~$1,400** | A working, world-first autonomous swarm. Enough for research, validation, and live detection against public OSINT. |
| **B — Essential paid** | **~$5,500** | Real commercial-grade pivot depth. The moment Sirens needs to stand next to Recorded Future–style output. |
| **C — Enterprise** | **~$25–30 k** | Parity with top-tier commercial TI stacks. Deferrable until product-market fit. |

**Proposed starting posture:** launch on **Scenario A** through Phases 0–7. Upgrade to **Scenario B** only after Phase 3 benchmarks show free-tier ceiling. Re-evaluate **C** only once paying customers or a funded engagement justifies it.
