# Sirens — Threat-Hunting / DFIR Agent Swarm: Research Survey

> **Status:** Research artifact. Not yet a build.
> **Scope:** Identify the winning mix of open-source projects to weave into *Sirens*, a multi-agent swarm covering threat hunting, DFIR, detection engineering, OSINT research, and active defence.

---

## 1. Executive Summary

No single project on GitHub implements a complete threat-hunting / DFIR swarm. Four or five mature projects each own one layer; Sirens is the glue. The shape is **one supervisor over four swarms, with a shared knowledge graph and an optional deception swarm**:

- **Supervisor** — LangGraph (from `soctalk`), enforcing routing, HITL gates, budgets, scope allow-lists, and legal guardrails.
- **Research swarm** — online OSINT collection, pivot, attribution (SpiderFoot / Mihari / ThreatIngestor / IntelOwl / abuse.ch / OTX / Shodan / Censys / GreyNoise / Ahmia).
- **Hunt swarm** — SIEM-side detection (Wazuh + Sigma + OTRF ThreatHunter-Playbook).
- **IR / DFIR swarm** — endpoint forensics (Velociraptor, GRR, Timesketch, Plaso).
- **Detection-engineering swarm** — authoring Sigma / YARA / Nuclei rules, iterating via a CTI-REALM-style reward loop.
- **Knowledge layer** — OpenCTI (STIX 2.1 graph) + MISP (IOC sharing) + TheHive (cases).
- **Deception swarm** (Sirens-specific, active-tracking posture) — Canarytokens, OpenCanary, Modern Honey Network, T-Pot, DNSChef/BIND-RPZ sinkholes.

Everything in the swarms is glued with **MCP** so agents speak one tool protocol. Standards: **STIX 2.1**, **MITRE ATT&CK**, **Sigma / YARA / Nuclei YAML**, **MISP events**.

---

## 2. The Winning Combination

| Layer | Project(s) | Role | License | Status (2026) |
|---|---|---|---|---|
| Supervisor / orchestration | [`soctalk`](https://github.com/gbrigandi/soctalk) (LangGraph) | Router, HITL, budgets, policy | Apache-2.0 | Production |
| Tool binding | `mcp-server-wazuh` / `-cortex` / `-misp` / `-thehive` ([gbrigandi](https://github.com/gbrigandi)) | LLM↔tool contract | MIT | Production (extend for IntelOwl, OpenCTI, Velociraptor, SpiderFoot, Canarytokens) |
| Hunt (SOC) | [Wazuh](https://github.com/wazuh/wazuh) + [Sigma](https://github.com/SigmaHQ/sigma) + [OTRF ThreatHunter-Playbook](https://github.com/OTRF/ThreatHunter-Playbook) | Log/endpoint hunts + playbooks | GPL-2.0 / Apache-2.0 | Production |
| DFIR | [Velociraptor](https://github.com/Velocidex/velociraptor), [GRR](https://github.com/google/grr), [Timesketch](https://github.com/google/timesketch), [Plaso](https://github.com/log2timeline/plaso) | Endpoint collection + timeline | Apache-2.0 | Production (no agent wrappers yet — glue needed) |
| Detection engineering | [CTI-REALM](https://www.microsoft.com/en-us/security/blog/2026/03/20/cti-realm-a-new-benchmark-for-end-to-end-detection-rule-generation-with-ai-agents/) (methodology), [SigmaGen](https://blogs.night-wolf.io/sigmagen-ai-powered-attck-mapped-threat-detection-with-sigma-rules), [Uncoder AI](https://socprime.com/blog/uncoder-ai-automates-mitre-attck-tagging-in-sigma-rules/) | Iterate rules against telemetry | Mixed / Research | Research-grade loop |
| Enrichment | [IntelOwl](https://github.com/intelowlproject/IntelOwl) | ~100 analyzers, one API | AGPL-3.0 | Production |
| Knowledge graph | [OpenCTI](https://github.com/OpenCTI-Platform/opencti) | STIX 2.1 memory, actor/infra pivot | Apache-2.0 | Production |
| IOC sharing | [MISP](https://github.com/MISP/MISP) | Events + feeds + community | AGPL-3.0 | Production |
| Case mgmt | [TheHive](https://github.com/TheHive-Project/TheHive) + [Cortex](https://github.com/TheHive-Project/Cortex) | HITL review + response queue | AGPL-3.0 | Production |
| MITRE scaffolds | [Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills) | 754 skills, ATT&CK/D3FEND/NIST/ATLAS | Apache-2.0 | Ready |
| OSINT / research | [SpiderFoot](https://github.com/smicallef/spiderfoot), [Mihari](https://github.com/ninoseki/mihari), [ThreatIngestor](https://github.com/InQuest/ThreatIngestor), [theHarvester](https://github.com/laramies/theHarvester), [Recon-ng](https://github.com/lanmaster53/recon-ng), [Harpoon](https://github.com/Te-k/harpoon) | Online collection | MIT / GPL-2.0 | Production |
| Dark/deep web | [Ahmia](https://ahmia.fi/), [TorBot](https://github.com/DedSecInside/TorBot), [deepdarkCTI](https://github.com/fastfire/deepdarkCTI), [Telerecon](https://github.com/sockysec/Telerecon), [Tosint](https://github.com/drego85/tosint) | Passive Tor + Telegram | Mixed OSS | Mature |
| Detection output | [Sigma](https://github.com/SigmaHQ/sigma), [YARA](https://github.com/VirusTotal/yara), [Nuclei](https://github.com/projectdiscovery/nuclei) + [nuclei-templates](https://github.com/projectdiscovery/nuclei-templates) | Rule artifacts | Mixed OSS | Production |
| CVE/exploit intel | [NVD API](https://nvd.nist.gov/developers/vulnerabilities), [CISA KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog), [VulnCheck](https://vulncheck.com/), [ExploitDB](https://www.exploit-db.com/), [PoC-in-GitHub](https://github.com/nomi-sec/PoC-in-GitHub) | Vulnerability context | Free APIs | Production |
| Deception (Sirens) | [Canarytokens](https://github.com/thinkst/canarytokens), [OpenCanary](https://github.com/thinkst/opencanary), [Modern Honey Network](https://github.com/pwnlandia/mhn), [T-Pot](https://github.com/telekom-security/tpotce), [HoneyDB](https://honeydb.io/), [DNSChef](https://github.com/iphelix/dnschef), BIND RPZ | Honey-tokens, honeypots, sinkholes | Mixed OSS | Production |

---

## 3. Architecture — Four Swarms + Knowledge + Deception

```
                 ┌─────────────────────────────────────────┐
                 │  Supervisor (LangGraph, soctalk-based)  │
                 │  routing • HITL • budgets • policy      │
                 └──────┬───────────────────────────┬──────┘
                        │  MCP  (one tool protocol) │
   ┌──────────┬─────────┼─────────┬─────────────────┼──────────┐
   ▼          ▼         ▼         ▼                 ▼          ▼
RESEARCH    HUNT      IR/DFIR   DETECTION      DECEPTION    KNOWLEDGE
(OSINT)     (SOC)               ENGINEERING    (Sirens)     (shared)
──────────  ──────    ─────────  ────────────  ──────────   ─────────
SpiderFoot  Wazuh     Velociraptor  Sigma      Canarytokens  OpenCTI
Mihari      Sigma     GRR           YARA       OpenCanary    MISP
ThreatIng.  ATT&CK    Timesketch    Nuclei     MHN           TheHive
IntelOwl    OTRF-THP  Plaso         CTI-REALM  T-Pot         Neo4j
abuse.ch                            Uncoder    DNSChef/RPZ
OTX / VT                                       sinkholes
Shodan / Censys
GreyNoise
Ahmia / Tor
GitGuardian / dorks
```

Each swarm is a LangGraph subgraph; nodes are agents; edges are policy-gated. All persistent state flows through **OpenCTI (graph) + MISP (IOCs) + TheHive (cases)**. Deception telemetry is a first-class collector feeding back into the Research swarm.

### 3.1 Research swarm

- **Projects:** SpiderFoot, Mihari, ThreatIngestor, IntelOwl, abuse.ch (MalwareBazaar / URLhaus / ThreatFox), AlienVault OTX, VirusTotal, Shodan, Censys, GreyNoise, Ahmia, theHarvester, Recon-ng, Harpoon.
- **Agents:** Planner, Collector (per source family), Enricher, Correlator, Analyst, Reporter. See §4.
- **APIs / function calls:** `spiderfoot.start_scan` / `get_scan_summary`; `intelowl.submit_observable` / `get_job`; abuse.ch REST (`/api/v1/get`); OTX `/api/v1/pulses/subscribed`; Shodan `/host/{ip}`; Censys `/v2/hosts/search`; GreyNoise `/v3/community/{ip}`; VirusTotal `/files/{hash}`; Ahmia search JSON.
- **State:** Writes STIX 2.1 bundles + MISP events + indicator labels into OpenCTI / MISP. Reads prior campaign graph from OpenCTI for pivot.
- **MCP broker:** **to-write** — `sirens-mcp-intelowl`, `sirens-mcp-opencti`, `sirens-mcp-spiderfoot`. Direct REST for abuse.ch / OTX / Shodan / Censys / GreyNoise / VT inside Collector tools.

### 3.2 Hunt swarm (SOC)

- **Projects:** Wazuh (indexer + manager), SigmaHQ rule-packs, OTRF ThreatHunter-Playbook, Elastic Common Schema.
- **Agents:** Hypothesis-Planner (reads OTRF playbook), Query-Writer (Sigma → Wazuh KQL / OpenSearch DSL), Triage-Analyst (scores hits against OpenCTI context), Escalator (opens TheHive case).
- **APIs / function calls:** Wazuh REST `/agents`, `/alerts`; OpenSearch `_search`; Sigma→backend translation via [`pySigma`](https://github.com/SigmaHQ/pySigma) + `pysigma-backend-opensearch`; `thehive.create_case`.
- **State:** Reads telemetry from Wazuh indexer, playbooks from git submodule, IOC context from OpenCTI. Writes cases to TheHive; reinforces detection gaps into the Detection-Engineering swarm queue.
- **MCP broker:** `mcp-server-wazuh` (vendored from gbrigandi), `mcp-server-thehive` (vendored). pySigma runs in-process in the agent.

### 3.3 IR / DFIR swarm

- **Projects:** Velociraptor (primary), GRR (secondary), Timesketch, Plaso, Volatility3 (memory), dfir-iris (case).
- **Agents:** Collector (chooses Velociraptor artifact packs), Timeline-Builder (plaso → Timesketch), Memory-Analyst (Volatility3 plugins), Root-Cause-Writer.
- **APIs / function calls:** Velociraptor gRPC `CollectArtifact` / `GetFlow` / `VFSListDirectory` / raw VQL; Timesketch REST `/api/v1/sketches/{id}/timelines`; Plaso `log2timeline.py` / `psort.py`; Volatility3 `vol.py -f <image> <plugin>`.
- **State:** Attaches flow results + timelines to the TheHive case; promotes confirmed IOCs into OpenCTI and MISP.
- **MCP broker:** **to-write** — `sirens-mcp-velociraptor` (done, Phase 2). Timesketch / Plaso / Volatility: glue CLIs via a thin MCP wrapper (**gap**).

### 3.4 Detection-Engineering swarm

- **Projects:** SigmaHQ, YARA, Nuclei + nuclei-templates, Uncoder AI (Sigma↔backend), SigmaGen (LLM-to-Sigma), CTI-REALM (benchmark methodology), Splunk Attack Range / [HELK](https://github.com/Cyb3rWard0g/HELK) (controlled telemetry).
- **Agents:** Rule-Author (LLM drafts Sigma/YARA/Nuclei from ATT&CK technique + campaign bundle), Rule-Tester (runs against captured telemetry in HELK/Attack-Range), Rule-Tuner (iterates on FP/FN), Rule-Publisher (PR to internal SigmaHQ fork).
- **APIs / function calls:** `yara.compile`; `nuclei -t {template} -target {sandbox}`; pySigma backend conversion; Splunk Attack Range Lambda APIs; telemetry playback via Wazuh indexer.
- **State:** Reads ATT&CK mappings + campaign STIX bundles from OpenCTI. Writes published rules as git artifacts; reward-loop scores stored per rule (for the reward loop — gap §7).
- **MCP broker:** **to-write** — light wrappers around `yara` / `nuclei` / `pysigma` (**gap**). Code-commit operations via git, not MCP.

### 3.5 Deception swarm (Sirens-specific)

- **Projects:** Thinkst Canarytokens (self-hosted), OpenCanary, Modern Honey Network, T-Pot, DNSChef, BIND RPZ.
- **Agents:** Placement-Planner (decides what token / decoy goes where, per scope allow-list `honey_tokens` block), Deployer (calls `canarytokens.create_token` / OpenCanary config push), Callback-Watcher (tails MHN + Canarytokens history), Sinkhole-Operator (publishes RPZ zones for owned / court-authorised domains only).
- **APIs / function calls:** Canarytokens REST `/generate`, `/history`, `/disable`; OpenCanary config via Ansible; MHN REST `/api/sessions`; BIND RPZ via `rndc reload` on owned resolver.
- **State:** Every callback becomes a high-fidelity IOC written to OpenCTI + MISP, tagged `sirens:deception:<campaign>`.
- **MCP broker:** **to-write** — `sirens-mcp-canarytokens` (done, Phase 2). OpenCanary / MHN / BIND-RPZ: **gap**, likely a `sirens-mcp-deception-ops` wrapper.

### 3.6 Knowledge layer (shared)

- **Projects:** OpenCTI + Neo4j + Elasticsearch + Redis + MinIO + RabbitMQ, MISP + MariaDB, TheHive + Cortex + Cassandra.
- **Agents:** None — this is substrate. The swarms read/write via MCP.
- **APIs / function calls:** OpenCTI GraphQL via `pycti` (`stix_domain_object.create`, `indicator.create`, `report.create`, `stix_core_relationship.create`, `label.create`); MISP REST (`/events/add`, `/attributes/add`, `/tags/attachTagToObject`); TheHive v5 REST (`/api/v1/case`, `/api/v1/task`, `/api/v1/observable`); Cortex analyzer launch.
- **State:** This IS the state. TLP markings + Sirens-specific markings (`SIRENS:INTERNAL`, `SIRENS:ATTRIBUTION_DRAFT`, `SIRENS:ATTRIBUTION_VALIDATED`, `SIRENS:CUSTOMER_PRIVATE`) bootstrapped via `compose/bootstrap/opencti_markings.py`.
- **MCP broker:** `sirens-mcp-opencti` (done, Phase 2), `mcp-server-misp` + `mcp-server-thehive` (vendored from gbrigandi), `mcp-server-cortex` (vendored).

---

## 4. Research Arm — Pipeline Spec

Tasking → Artifacts in ≤5 min target.

1. **Planner** — parses tasking (`track Scattered Spider infra`, `watch Akira leaks`) into a query DAG.
2. **Collector fan-out** — one agent per source family, parallel:
   - **Malware**: abuse.ch (MalwareBazaar / URLhaus / ThreatFox), VirusTotal, Hybrid Analysis, Triage
   - **Infra**: Shodan, Censys, GreyNoise, FOFA, ZoomEye, Validin, Silent Push
   - **Passive DNS**: Farsight DNSDB, DomainTools, Mnemonic *(paid)*
   - **TI platforms**: AlienVault OTX, MISP feeds, OpenCTI connectors, Pulsedive, IBM X-Force
   - **Leaks**: GitGuardian, GitHub/Gist dorks, Pastebin mirrors (ToS-aware)
   - **Social**: X, Mastodon, Telegram public, Reddit r/netsec, The DFIR Report, BleepingComputer
   - **Dark web (passive)**: Ahmia, dark.fail, deepdarkCTI
   - **CVE/exploit**: NVD, CISA KEV, VulnCheck, ExploitDB, nuclei-templates, PoC-in-GitHub
   - **Deception telemetry** (owned): Canarytokens, OpenCanary, MHN, T-Pot, sinkhole zones
3. **Enricher** — one call to IntelOwl → ~100 analyzer outputs.
4. **Correlator** — pivot in OpenCTI: actor ↔ malware ↔ domain ↔ IP ↔ registrant ↔ adjacent actor.
5. **Analyst** — LLM summarises campaign; tags MITRE ATT&CK TTPs via Anthropic-Cybersecurity-Skills.
6. **Reporter** — emits STIX 2.1 bundle + MISP event + draft Sigma/YARA/Nuclei + TheHive case (HITL if actionable).

---

## 5. Active-Tracking Layer (Sirens Posture)

| Capability | OSS | Authorization required before live |
|---|---|---|
| Honey-tokens in owned env | Canarytokens, CanaryPy | Internal only |
| Honeypots on owned infra | OpenCanary, MHN, T-Pot | Internal only |
| DNS sinkhole of owned / expired / court-authorised domains | DNSChef, BIND RPZ | Domain title or court/registrar order |
| Scripted decoy responses on owned honeypots | OpenCanary / T-Pot modules | Internal only |
| Passive C2 tracking | Shodan + Censys + passive DNS | None (read-only public data) |
| Attribution artifacts → MISP with TLP marking | MISP | TLP policy approved |

**Hard line:** no unauthorized access, no use of leaked credentials, no scraping that violates ToS, no interaction with attacker-controlled infrastructure unless we own it or have explicit written authorization. CFAA / CMA / NIS2 review required before activating any aggressive capability.

---

## 6. Boundary Formats

- **Research → Knowledge:** STIX 2.1 bundle
- **Knowledge → Hunt:** MISP feed + Sigma rules
- **Hunt → IR:** TheHive case
- **IR → Knowledge:** STIX 2.1 incident + ATT&CK technique tags
- **Detection engineering → Hunt:** Sigma / YARA / Nuclei YAML
- **All LLM ↔ tool:** MCP

---

## 7. Gaps (Sirens Must Write)

1. MCP servers for **IntelOwl, OpenCTI, SpiderFoot, Velociraptor, Canarytokens**.
2. Supervisor middleware: budget, rate-limit, scope allow-list, ethics/legal gate.
3. **Deception-swarm controller** — honeypot projects lack an agent interface.
4. Unified **research-tasking schema** for the Planner.
5. **Detection-engineering reward loop** (CTI-REALM is a benchmark, not a product).
6. Telegram / Discord / X collectors built strictly to official API terms.
7. STIX 2.1 converter harmonising multi-source observable quirks.

---

## 8. Key Sources

Projects linked inline above. Papers / industry sources:

- *Policy-Guided Threat Hunting: An LLM-enabled Framework with Splunk SOC Triage* — arXiv [2603.23966](https://arxiv.org/abs/2603.23966) (March 2026)
- *A Survey on Agentic Security: Applications, Threats and Defenses* — arXiv [2510.06445](https://arxiv.org/abs/2510.06445) (Oct 2025)
- *AI-Augmented SOC: A Survey of LLMs and Agents for Security Automation* — [MDPI 5/4/95](https://www.mdpi.com/2624-800X/5/4/95) (2025)
- [CTI-REALM benchmark](https://www.microsoft.com/en-us/security/blog/2026/03/20/cti-realm-a-new-benchmark-for-end-to-end-detection-rule-generation-with-ai-agents/) (Microsoft, March 2026)
- [Recorded Future — Autonomous Threat Operations](https://www.recordedfuture.com/products/autonomous-threat-operations)
- [VirusTotal agentic guide](https://gtidocs.virustotal.com/docs/agentic-user-guide)
- [Microsoft Agent Governance Toolkit](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/)

---

## 9. Recommended Build Order

See `sirens-build-plan.md`.
