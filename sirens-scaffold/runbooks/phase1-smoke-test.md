# Runbook — Phase 1 Smoke Test: DFIR Report Ingest

**Owner:** Sirens ops
**Trigger:** Gate for Phase 1 exit.
**Severity at failure:** SEV3 (blocks Phase 2 kickoff).
**Expected duration:** ~15 min.

Goal: prove STIX round-trips end-to-end through the knowledge spine with no
agent code. If this works manually, Phase 2 has a stable target.

---

## 1. Pick a source report

Use the most recent DFIR Report article that is **not** already referenced by
any indicator in OpenCTI (so we can tell the difference between seed data
and what we just added).

```
https://thedfirreport.com/          # pick latest
```

Copy the URL. For this runbook, placeholder: `<REPORT_URL>`.

---

## 2. Import the report into MISP

MISP ships a built-in URL importer that produces a new event.

**Option A — MISP UI:**

1. Event Actions → Import from → URL.
2. Paste `<REPORT_URL>`.
3. Distribution: "Your organisation only" (we'll TLP on OpenCTI side).
4. Threat Level: Medium. Analysis: Initial. Info: `DFIR Report smoke-test`.
5. Submit. Click "Publish" once the import settles.

**Option B — one-shot from the host:**

```bash
curl -sk https://localhost/events/freeTextImport \
  -H "Authorization: ${MISP_ADMIN_KEY}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d "{\"value\":\"$(curl -sL <REPORT_URL> | html2text)\"}"
```

Record the MISP event ID returned — call it `<MISP_EVENT_ID>`.

**Expected:** MISP extracts ≥ 5 indicators (IPs, domains, hashes) and tags
MITRE ATT&CK techniques where the report mentions them.

---

## 3. Propagate to OpenCTI via the MISP connector

The MISP connector for OpenCTI (add it now if not running in §4 of the boot
runbook; image `opencti/connector-misp:6.4.6`) will pick up the published
event on its next poll (default 5 min).

Check:

```bash
docker compose logs -f connector-misp | grep -i "<MISP_EVENT_ID>"
```

When you see `Processing event <MISP_EVENT_ID>`, open OpenCTI UI →
Analyses → Reports → filter by title; the DFIR Report should appear as a
`Threat-Report` with observables linked.

---

## 4. Manual case in TheHive

With the MISP event live:

1. TheHive UI → New Case → "MISP import" wizard.
2. Pick the event by ID `<MISP_EVENT_ID>`.
3. Assign yourself, TLP:AMBER, PAP:AMBER.
4. Create case.

**Expected:** case contains one observable per MISP attribute, and running
the Cortex `MISP_2_1` analyzer on any indicator returns a hit.

---

## 5. STIX round-trip

Export the OpenCTI report as STIX 2.1:

```bash
curl -s "http://localhost:8080/graphql" \
  -H "Authorization: Bearer ${OPENCTI_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query($id: String!) { reportExport(id: $id, format: \"application/stix+json;version=2.1\") }",
    "variables": {"id": "<REPORT_ID_FROM_OPENCTI>"}
  }' | jq '.data.reportExport' -r | tee /tmp/smoke.stix.json | jq '.objects | length'
```

**Expected:** ≥ 10 STIX objects (report, identities, indicators, malware,
attack-patterns, relationships).

Re-import the file back in via OpenCTI UI → Data → Import → upload
`/tmp/smoke.stix.json`. It should match and update existing objects (no
duplicates). This proves STIX serializes and deserializes cleanly.

---

## 6. Pass / fail

Phase 1 passes when **all** of the following are true:

- [ ] MISP event created, published, ≥ 5 attributes extracted
- [ ] OpenCTI has a matching `Threat-Report` with linked observables
- [ ] At least one ATT&CK technique tag propagated from MISP → OpenCTI
- [ ] TheHive case created with the same observables
- [ ] A Cortex analyzer runs green on at least one observable
- [ ] OpenCTI STIX export produces valid STIX 2.1 with ≥ 10 objects
- [ ] Re-import of the same STIX does not create duplicates

If any item fails, file an issue tagged `phase:1 blocker` and hold Phase 2.

---

## 7. Cleanup

Leave the smoke-test data in place — it becomes the seed corpus for Phase 2
integration tests. Tag the OpenCTI report with `SIRENS:INTERNAL` and the
MISP event with a `tlp:amber` tag so downstream agents can distinguish
smoke-test state from production data.
