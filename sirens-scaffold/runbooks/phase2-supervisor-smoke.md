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

## 3. Vendored MCP smoke tests

For each of `wazuh`, `cortex`, `misp`, `thehive`:

```bash
cd mcp-servers/vendored/<server>
docker build -t sirens-mcp-<server>:dev .
# Each upstream ships its own README — follow it for the single-tool probe.
```

Exit criteria: each vendored server answers its simplest read-only tool
(e.g. `misp.get_event_by_id`, `thehive.get_case`).

---

## 4. Exit criteria

- [ ] `pytest tests/unit/test_supervisor_golden_path.py` green
- [ ] IntelOwl MCP `list_analyzers` returns ≥ 20 entries
- [ ] IntelOwl MCP refuses a call with no `x-tasking-id`
- [ ] All four vendored MCP servers pass their upstream smoke test
- [ ] Audit log written (inspect `$SIRENS_AUDIT_SINK` or stderr)

If any item fails, file an issue tagged `phase:2 blocker` and hold Phase 3.
