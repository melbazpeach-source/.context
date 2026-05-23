# Sirens Scaffold — Phase 0 → 4 Review

**Date:** 2026-04-22
**Scope:** Honest walkthrough of everything shipped in
`sirens-scaffold/` before Phase 4.1 (LiveDispatch) starts. What's real,
what's stubbed, what's missing, and what's load-bearing coupling that
mustn't rot.

---

## 1. What's shipped

### 1.1 Schemas (`schemas/`)

| File | Notes |
|---|---|
| `tasking.py` | Tasking, Target, Posture, TLP, Budget, Authorization. Pydantic v2, `SCHEMA_VERSION = "1.0.0"`. |
| `agent_message.py` | AgentMessage with Audit / Provenance / ToolCall. `extra="forbid"` — strict. |
| `research.py` | Research-swarm artifacts (ResearchQuery → …→ ResearchReport). |
| `hunt.py` | Hunt-swarm artifacts (Hypothesis → …→ HuntReport / HuntCase). |

All schemas carry `SCHEMA_VERSION` but **no runtime version check** —
consumers trust the producer. Drift risk on day one.

### 1.2 Supervisor (`agents/supervisor/`)

- `state.py` — TypedDict + `_append` reducer + BudgetLedger.
- `policy.py` — `ScopeAllowlist` loader. Matchers: `covers`, `forbids`,
  `allows_collector`, `window_active`. **Exact-string match only — no
  wildcard / CIDR / regex.** A CVE target must be enumerated verbatim.
- `middleware/{ethics,scope,budget,rate_limit,audit}.py` — five gates,
  invoked from the intake / finalize nodes.
- `nodes.py` — intake → plan → dispatch → finalize. `make_dispatch` is a
  factory closing over the swarm registry; merges subgraph audit into
  the ledger before finalize.
- `graph.py` — `build_supervisor_graph(allowlist, swarms=None)`.
- `subgraphs.py` — registers `"research"` + `"hunt"` under StubDispatch.

### 1.3 Research swarm (`agents/research/`)

Six nodes: planner → collector → enricher → correlator → analyst →
reporter. `ResearchDispatch` Protocol, `StubDispatch` default. Zero-query
short-circuit to reporter.

### 1.4 Hunt swarm (`agents/hunt/`)

Five nodes: hypothesis_planner → query_writer → hunter → triage →
escalator. `HuntDispatch` Protocol, `StubDispatch` default.
Zero-hypothesis short-circuit to escalator. Case opens when
`CONFIRMED + SUSPICIOUS ≥ escalation_threshold` (hard-coded default 3).

### 1.5 MCP servers (`mcp-servers/`)

- Written here: `intelowl`, `opencti`, `spiderfoot`, `velociraptor`,
  `canarytokens`. Five tools each (ish). All enforce `x-tasking-id`; a
  few enforce `x-active-authorization` for arbitrary / non-passive tools.
- Vendored (expected via submodule): `wazuh`, `cortex`, `misp`, `thehive`
  from `gbrigandi/*`. **The submodules are NOT actually added yet — only
  a README exists in `mcp-servers/vendored/`.**

### 1.6 Knowledge spine (`compose/`)

- `docker-compose.knowledge.yml` + `connectors.yml` + `mcp.yml`.
- Bootstrap: `opencti_markings.py` + `misp_feeds.py` — both idempotent,
  feed identification by (provider, url) tuple.

### 1.7 Skills (`skills/`)

- `anthropic-cybersecurity-skills` submodule pinned at `888bbe4` (754
  skills). No code reads from it yet.

### 1.8 Tests

- 13 unit tests, all green.
- **Zero integration tests.** Nothing touches a live docker-compose stack.

### 1.9 Runbooks

- `knowledge-spine-boot.md`, `phase1-smoke-test.md`, `phase2-supervisor-smoke.md`,
  `phase3-research-smoke.md`, `phase4-hunt-smoke.md`. Exit-gate style.

### 1.10 Research artifacts (`../.context/research/`)

Survey, build plan, cost analysis. Already committed.

---

## 2. What's actually proven vs what's shape-only

| Claim | Proven? |
|---|---|
| Schemas validate | ✅ pydantic catches malformed inputs |
| Graph wiring runs end-to-end | ✅ 13 tests, audit log chains through |
| Supervisor routes by TaskingType | ✅ unit test per mapping |
| Budget gate trips on overspend | ✅ test uses synthetic audit |
| Subgraph audit folds into ledger | ✅ test with FakeSubgraph |
| Scope allow-list blocks out-of-scope | ✅ test |
| Posture mismatch blocks | ✅ test |
| MCP servers speak MCP | ⚠️ **unverified** — servers written but never run |
| `x-tasking-id` enforcement | ⚠️ written, no test |
| Canarytokens webhook allow-list fail-closed | ⚠️ written, no test |
| Velociraptor `run_vql` active-authorization gate | ⚠️ written, no test |
| Research LiveDispatch | ❌ doesn't exist |
| Hunt LiveDispatch | ❌ doesn't exist |
| Docker Compose brings stack up | ❌ untested; vendored submodules missing |
| MISP / TheHive / Cortex / Wazuh MCP servers | ❌ submodules not added |
| Skill-library consumer code | ❌ nothing reads the 754 skills |
| Sigma rule-pack | ❌ not vendored |

---

## 3. Load-bearing design choices (don't rot these)

1. **Single Tasking shape crosses every boundary.** Scope gate, LangGraph
   state, every subgraph, every MCP call. If `Tasking` grows
   backwards-incompatible, everything breaks. Version-gate before
   mutating.

2. **AgentMessage is the unit of audit.** Ledger merge pulls directly
   from `AgentMessage.audit`. LiveDispatch MUST populate `input_tokens`,
   `output_tokens`, `cost_usd`, `tool_calls` accurately on every emitted
   message — else the budget gate is a placebo.

3. **Dispatch Protocol + StubDispatch pattern.** Every swarm follows
   this. New swarms (IR, Detection, Deception) should mirror it:
   - `<Swarm>Dispatch(Protocol)` naming convention
   - `StubDispatch` in the same `dispatch.py` file
   - `make_*` closure factories for every node
   - Conditional-edge short-circuit from the first node for empty cases

4. **Scope allow-list is the only place YAML is parsed into policy.**
   Don't fork the matcher logic into middleware — leave it in
   `policy.py`.

5. **MCP header contract:** `x-tasking-id` required; `x-active-authorization`
   for arbitrary / non-passive tools; fail-closed webhook allow-list on
   Canarytokens. New MCP servers must preserve this contract.

6. **Ledger merge runs only on subgraph messages, not the STATUS
   preamble.** The preamble is supervisor-owned and always zero-audit. If
   a future supervisor node starts emitting non-zero audit, revisit the
   merge.

---

## 4. Concrete gaps / debt

### 4.1 Blocking Phase 4.1

- Vendored MCP submodules (wazuh, cortex, misp, thehive) not added —
  `docker compose -f docker-compose.mcp.yml up` fails today.
- No Sigma rule-pack to lookup against. (Landing next per user's plan.)
- Escalation threshold hard-coded. Should move to the scope allow-list.
- LiveDispatch classes do not exist for either swarm.

### 4.2 Blocking any live run

- **TLP enforcement.** TLP is carried on every schema but nothing checks
  that a REPORT's marking is ≥ the Tasking's TLP. A compromised Analyst
  could emit TLP:CLEAR reports against a TLP:RED tasking.
- Schema versioning is advisory, not enforced.
- No integration tests — code has only been exercised with StubDispatch.
- `ScopeAllowlist.covers()` is exact-string match. CVE, domain, IP with
  wildcards / CIDR not supported.

### 4.3 Quality / observability

- Audit log is fire-and-forget; no integrity / tamper check.
- Mid-stream audit granularity is coarse — everything lands in the
  terminal REPORT message's `audit`. Per-ToolCall timing exists in the
  schema but nothing populates it mid-run.
- Ruff / mypy policy is inconsistent (22 lint warnings pre-existing,
  new code matches local style).

### 4.4 Ops / legal

- No runbooks for: oncall, backup-restore, key-rotation, legal-incident,
  feed-poisoning, cost-runaway, deception-callback, customer-handover.
- The scope allow-list template exists in `docs/` but nobody has filled
  one in. The first real engagement will need counsel to sign one first.

---

## 5. What I'd tighten before going any further

In order of payoff:

1. **Add the vendored MCP submodules** (wazuh, cortex, misp, thehive).
   One command each. Unblocks docker-compose.
2. **Enforce TLP downgrade as a middleware check** in supervisor
   `finalize`. 20 lines. Real security posture, not a doc.
3. **Land the Sigma rule-pack submodule** (next task per plan).
4. **Write a `LiveDispatch` skeleton for Research** that does nothing
   but populate `AgentMessage.audit` correctly — prove the ledger-merge
   contract end-to-end with a real-ish flow, even if `enrich` still
   returns empty data.
5. **One integration test** — docker-compose up the knowledge spine,
   run the Phase 1 smoke, tear down. Gates any change that touches
   compose files.

---

## 6. What NOT to do next

- Don't build Phase 5 (IR/DFIR) yet. Three swarms is enough to prove the
  pattern. Going wider before going live in Research + Hunt just
  multiplies scaffolding that'll need to change once LiveDispatch finds
  problems with the contracts.
- Don't write LLM-driven Planner logic before LiveDispatch exists. The
  static-map planner is fine; re-implementing it against a Claude call
  adds cost without proving anything new.
- Don't try to move the scaffold to `melbazpeach-source/Sirens` yet.
  Submodule paths + MCP broker paths + compose references all change;
  do it once when the scaffold is otherwise stable.

---

## 7. Green-light summary

**Safe to build next:** Sigma rule-pack submodule. Vendored MCP
submodules. TLP-downgrade middleware. A minimal LiveDispatch for
Research.

**Hold until infrastructure is ready:** Full LiveDispatch wiring.
Integration tests. Repo move.

**Re-plan before next start:** Phase 5 (IR) — revisit after Research +
Hunt go live; the contract may drift.
