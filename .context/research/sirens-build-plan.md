# Sirens — Step-by-Step Build Plan

> **Companion to:** `sirens-swarm-survey.md`
> **Philosophy:** Stand up the knowledge spine first, then the Research Arm against free APIs, then layer in Hunt / IR / Detection-Engineering / Deception. Defer paid feeds and dark-web until after free-tier validation.

---

## Phase 0 — Foundations (Week 0–1)

**Goal:** environment, repo layout, legal sign-off.

1. Provision infrastructure: 1× dedicated host (32 GB RAM, 8 vCPU, 500 GB NVMe) for the knowledge stack; 1× smaller host for Wazuh indexer.
2. Create repo `sirens/` with sub-trees: `compose/`, `agents/`, `mcp-servers/`, `prompts/`, `schemas/`, `docs/`, `tests/`, `runbooks/`.
3. Secrets vault (Doppler / 1Password / HashiCorp Vault) — API keys never in repo.
4. **Legal & ethics sign-off:** scope allow-list, CFAA/CMA/NIS2 review, TLP policy, data-minimisation policy, incident disclosure policy. Written authorization for any active-defence capability.
5. Observability baseline: Prometheus + Grafana + Loki, OpenTelemetry traces from every agent.

**Exit:** host ready, repo skeleton, legal green-light on paper.

---

## Phase 1 — Knowledge Spine (Week 1–2)

**Goal:** persistent memory before any agents exist.

1. `docker compose` bring-up: **OpenCTI** + **MISP** + **TheHive + Cortex** + **Neo4j** + **Elasticsearch** + **Redis**.
2. Load seed feeds into OpenCTI: MITRE ATT&CK STIX, AlienVault OTX, abuse.ch, CISA KEV.
3. Load MISP default feeds (CIRCL, abuse.ch, Botvrij).
4. Define OpenCTI marking-definition taxonomy (TLP:CLEAR / GREEN / AMBER / RED, Sirens-internal labels).
5. Smoke test: ingest one DFIR Report article by hand → STIX bundle in OpenCTI, MISP event created, TheHive case raised.

**Exit:** STIX round-trips end-to-end; graph queryable.

---

## Phase 2 — Supervisor + MCP (Week 2–3)

**Goal:** the agent backbone.

1. Fork / vendor `soctalk` supervisor; strip workflows we don't need.
2. Stand up existing MCP servers: `mcp-server-wazuh`, `-cortex`, `-misp`, `-thehive`.
3. Write new MCP servers in this order: **IntelOwl → OpenCTI → SpiderFoot → Velociraptor → Canarytokens**. One per sprint-week.
4. Supervisor middleware (new): budget cap, rate limit, scope allow-list, ethics/legal gate, audit log writer.
5. Define agent message schema (Pydantic) and tasking schema.
6. Golden-path test: supervisor receives a fake tasking, routes to a no-op agent, writes an audit row.

**Exit:** supervisor can dispatch to any tool via MCP under policy.

---

## Phase 3 — Research Arm MVP (Week 3–5)

**Goal:** the "go online and track hackers" capability, free-tier only.

1. Build six agents as LangGraph nodes: **Planner, Collector, Enricher, Correlator, Analyst, Reporter**.
2. Collector plugins (free only this phase): abuse.ch suite, AlienVault OTX, NVD, CISA KEV, Shodan free, Censys free, GreyNoise community, VirusTotal public, GitHub API, nuclei-templates, PoC-in-GitHub.
3. IntelOwl as the one-call enricher.
4. Correlator queries OpenCTI for pivots.
5. Analyst uses Anthropic-Cybersecurity-Skills scaffolds for ATT&CK tagging.
6. Reporter emits STIX 2.1 + MISP event + draft Sigma / YARA / Nuclei + TheHive case.
7. End-to-end benchmark: feed 5 recent DFIR Report URLs → measure time-to-bundle and recall against manual analysis.

**Exit:** Sirens produces STIX bundles and detection drafts from free sources unsupervised.

---

## Phase 4 — Hunt Swarm (Week 5–7)

**Goal:** detect attackers in your own telemetry.

1. Wazuh agents deployed to target endpoints; indexer hot-shard sized.
2. Import OTRF ThreatHunter-Playbook into a hunt library.
3. Hunt agents: **Hypothesis-Generator, Query-Writer, Evaluator, Escalator**.
4. Sigma rules from Phase 3 compiled to Wazuh detection content.
5. Escalator opens TheHive case on hit; Analyst from Research Arm re-invoked for context.

**Exit:** automated hunt cadence running nightly; hits triaged into TheHive.

---

## Phase 5 — Detection Engineering Swarm (Week 7–8)

**Goal:** rule quality improves itself.

1. Implement the **CTI-REALM reward loop**: draft rule → test against replay telemetry → score on TP/FP → iterate.
2. Uncoder AI integration for ATT&CK tagging.
3. Promotion pipeline: drafts → `staging/` → canary deploy to Wazuh → promote on clean 72 h.

**Exit:** rule drafts land with measurable precision / recall deltas.

---

## Phase 6 — IR / DFIR Swarm (Week 8–10)

**Goal:** respond, not just detect.

1. Velociraptor deployed; artifact collection library curated.
2. Agents: **Triage, Acquisition, Timeline-Builder, Scoper, Responder**.
3. Timesketch + Plaso for timeline; Timeline-Builder agent posts into Timesketch, Scoper annotates.
4. Responder is HITL-gated by default (isolate / kill / reimage all require human approval).

**Exit:** one full tabletop incident driven from detection → containment → timeline.

---

## Phase 7 — Deception Swarm (Sirens differentiator) (Week 10–12)

**Goal:** active defence with hard guardrails.

1. Deploy **Canarytokens** (internal doc canaries, AWS API-key canaries, Azure managed-identity canaries, Kubernetes canaries).
2. Deploy **OpenCanary** / **T-Pot** on owned infra in DMZ with segregated network.
3. **MHN** as the honeypot feed aggregator.
4. Stand up sinkhole authority (BIND RPZ + DNSChef) for domains Sirens owns or has court/registrar authorization over — never others.
5. Deception-swarm controller: monitors callbacks / interactions, emits STIX observables back into the Research Arm with `deception-sourced` marking.

**Exit:** first canary callback produces an attributed STIX bundle; sinkhole captures live-seen traffic to an owned domain.

---

## Phase 8 — Hardening & Launch (Week 12–14)

1. Chaos-test the supervisor (kill nodes, poison feeds, forged STIX).
2. Red-team the deception deployment from outside.
3. Full runbook set in `runbooks/` (on-call, backup, restore, key-rotation, legal-incident).
4. Public / private announce (Sirens v0.1).

---

## Team & Cadence

| Role | Count | Focus |
|---|---|---|
| Platform engineer | 1 | infra, compose, observability |
| Agent engineer | 1–2 | LangGraph nodes, MCP servers |
| Detection engineer | 1 | Sigma/YARA/Nuclei, CTI-REALM loop |
| DFIR analyst | 0.5 | runbooks, Velociraptor content, HITL triage |
| Legal / compliance | 0.25 | scope, authorizations, TLP |

Cadence: two-week sprints, demo each phase exit to a small internal audience before moving on.

---

## Dependencies Between Phases

```
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─┬─► Phase 4 ─► Phase 5 ─┐
                                          ├─► Phase 6 ────────────┤─► Phase 8
                                          └─► Phase 7 ────────────┘
```

Phases 4, 6, 7 can run in parallel after Phase 3 if staffing allows.

---

## Risk Register (top 5)

1. **LLM cost runaway** — mitigated by supervisor budget caps + Sonnet/Haiku routing for cheap steps.
2. **Legal exposure from active tracking** — mitigated by written scope allow-lists + mandatory HITL for any outbound action.
3. **Feed poisoning / adversarial STIX** — mitigated by provenance-marking + quarantine of new feeds for 72 h.
4. **Compose-stack fragility at knowledge layer** — mitigated by snapshotted Postgres / Neo4j backups nightly.
5. **Collector ToS drift** — mitigated by a monthly ToS-review cron and kill-switch per collector.

---

## Exit Criteria for v0.1 "Sirens Live"

- STIX bundles produced end-to-end, nightly.
- ≥80 % of hand-labelled DFIR-Report IOCs recovered automatically.
- ≥1 canary callback attributed back to an actor in OpenCTI.
- Runbooks reviewed, on-call rotation seeded.
- Legal + TLP policy signed off by counsel.
