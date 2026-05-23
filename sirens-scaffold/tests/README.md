# Sirens Tests

Three layers:

| Layer | Tooling | Lives in |
|---|---|---|
| Unit (schemas, supervisor middleware, MCP servers) | `pytest` | `tests/unit/` |
| Integration (compose stack up; agents talk to real MISP/OpenCTI/TheHive in throwaway containers) | `pytest` + `testcontainers` | `tests/integration/` |
| End-to-end (full swarm against a curated CTI corpus) | `pytest` + `CTI-REALM` benchmark subset | `tests/e2e/` |

## Smoke test (Phase 1 exit)

`tests/e2e/test_dfir_report_ingest.py`:

1. Pick one DFIR Report URL.
2. Submit as an `INGEST_REPORT` Tasking.
3. Within 5 minutes, expect: STIX bundle in OpenCTI, MISP event, TheHive
   case, ≥1 draft Sigma rule, ATT&CK technique tags ≥3.

## CI

GitHub Actions matrix: schemas + unit on every push; integration on PR;
e2e nightly.
