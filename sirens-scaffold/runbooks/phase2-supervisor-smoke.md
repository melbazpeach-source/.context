# Runbook — Phase 2 Supervisor Smoke Test

**Owner:** Sirens ops
**Trigger:** Gate for Phase 2 exit.
**Severity at failure:** SEV3 (blocks Phase 3 kickoff).
**Expected duration:** ~5 min automated + 15 min manual MCP check.

---

## 1. Automated golden-path tests

```bash
cd sirens
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/unit/test_supervisor_golden_path.py -v
```

Expected: 3 passing tests.

- `test_golden_path` — well-scoped Tasking → zero violations, STATUS message emitted.
- `test_out_of_scope_target_blocks` — target not in allow-list → short-circuit with scope violation.
- `test_posture_mismatch_blocks` — mismatched posture → rejected.

---

## 2. IntelOwl MCP smoke test

Prereqs: IntelOwl running and reachable (see upstream docs for bring-up).

```bash
cd mcp-servers/intelowl
pip install -e .
export INTELOWL_URL=https://intelowl.local
export INTELOWL_TOKEN=<issued-token>

# Run the server over stdio under the MCP Inspector
npx @modelcontextprotocol/inspector sirens-mcp-intelowl
```

In the Inspector UI:

1. Set request header `x-tasking-id: smoke-$(date +%s)`.
2. Call `list_analyzers` — expect a non-empty list.
3. Call `submit_observable` with `{observable: {value: "8.8.8.8", classification: "ip", tlp: "AMBER"}, playbook: "Dns"}`.
4. Poll `get_job` with the returned `job_id` until `status == "reported_without_fails"`.

Verify: a call without the `x-tasking-id` header is rejected — proves the
supervisor's audit invariant.

---

## 3. OpenCTI MCP smoke test

Prereqs: OpenCTI reachable at `$OPENCTI_URL`, admin token in `$OPENCTI_TOKEN`.

```bash
cd mcp-servers/opencti
pip install -e .
export OPENCTI_URL=http://localhost:8080
export OPENCTI_TOKEN=<OPENCTI_ADMIN_TOKEN from compose/.env>
npx @modelcontextprotocol/inspector sirens-mcp-opencti
```

In the Inspector UI, with `x-tasking-id: smoke-$(date +%s)`:

1. Call `list_reports` with `limit: 5` — expect the DFIR Report smoke
   run's report from Phase 1 to appear.
2. Call `create_indicator` with a safe test pattern, e.g.:
   ```json
   {
     "payload": {
       "pattern": "[ipv4-addr:value = '203.0.113.1']",
       "name": "sirens-smoke-203.0.113.1",
       "indicator_types": ["malicious-activity"],
       "confidence": 10
     }
   }
   ```
3. Call `search_entities` with `query: "sirens-smoke"` — expect one hit.
4. In OpenCTI UI, confirm the new indicator carries the
   `sirens:tasking:smoke-...` label.

Verify: any call without `x-tasking-id` is rejected.

---

## 4. SpiderFoot MCP smoke test

Prereqs: SpiderFoot OSS reachable (e.g. `http://localhost:5001`). No auth
required for OSS default.

```bash
cd mcp-servers/spiderfoot
pip install -e .
export SPIDERFOOT_URL=http://localhost:5001
npx @modelcontextprotocol/inspector sirens-mcp-spiderfoot
```

In the Inspector UI, with `x-tasking-id: smoke-$(date +%s)`:

1. Call `list_modules` — expect ≥ 200 entries.
2. Call `start_scan` with `{ "target": "example.com", "name": "sirens-smoke",
   "usecase": "Passive" }`. Expect a Scan record with `status: "CREATED"`
   or `"STARTING"`.
3. After ~2 min, call `get_scan_summary` with the returned id — expect
   at least one non-zero event-type row.
4. Call `start_scan` with `usecase: "Footprint"` and NO
   `x-active-authorization` header — expect a permission error. This
   is the ethics-gate regression.
5. Retry step 4 with header `x-active-authorization: true` — expect
   success. Abort with `stop_scan`.

---

## 5. Velociraptor MCP smoke test

Prereqs: Velociraptor server running with at least one enrolled client.
Generate an api-client config:

```bash
velociraptor config api_client --role=administrator \
  api.config.yaml sirens-mcp
```

Place the file at `./secrets/velociraptor-api.config.yaml`.

```bash
cd mcp-servers/velociraptor
pip install -e .
export VELOCIRAPTOR_CONFIG=$(pwd)/../../compose/secrets/velociraptor-api.config.yaml
npx @modelcontextprotocol/inspector sirens-mcp-velociraptor
```

With `x-tasking-id: smoke-$(date +%s)`:

1. Call `list_clients` with `search: "all"`, `limit: 5` — expect ≥ 1 client.
2. Call `list_artifacts` with `search: "^Generic\\.Client\\.Info$"` — expect 1.
3. Call `collect_artifact` with a known-safe read-only artifact, e.g.
   `Generic.Client.Info`, against the client from step 1. Expect a Flow
   with `state: "RUNNING"`.
4. Wait 30s, call `get_flow` — expect `state: "FINISHED"`.
5. Call `get_flow_results` with `artifact: "Generic.Client.Info"` —
   expect a row of metadata.
6. Call `run_vql` with `query: "SELECT 1 AS ok FROM scope()"` and
   NO active-authorization header — expect a permission error.
7. Retry step 6 with `x-active-authorization: true` — expect `[{"ok": 1}]`.

---

## 6. Vendored MCP smoke tests

For each of `wazuh`, `cortex`, `misp`, `thehive`:

```bash
cd mcp-servers/vendored/<server>
docker build -t sirens-mcp-<server>:dev .
# Each upstream ships its own README — follow it for the single-tool probe.
```

Exit criteria: each vendored server answers its simplest read-only tool
(e.g. `misp.get_event_by_id`, `thehive.get_case`).

---

## 7. Exit criteria

- [ ] `pytest tests/unit/test_supervisor_golden_path.py` green
- [ ] IntelOwl MCP `list_analyzers` returns ≥ 20 entries
- [ ] IntelOwl MCP refuses a call with no `x-tasking-id`
- [ ] OpenCTI MCP creates + retrieves a tagged smoke indicator
- [ ] OpenCTI MCP refuses a call with no `x-tasking-id`
- [ ] SpiderFoot MCP runs a Passive scan and returns a non-empty summary
- [ ] SpiderFoot MCP refuses a non-Passive scan without `x-active-authorization`
- [ ] Velociraptor MCP runs `Generic.Client.Info` end-to-end
- [ ] Velociraptor MCP `run_vql` refuses without `x-active-authorization`
- [ ] All four vendored MCP servers pass their upstream smoke test
- [ ] Audit log written (inspect `$SIRENS_AUDIT_SINK` or stderr)

If any item fails, file an issue tagged `phase:2 blocker` and hold Phase 3.
