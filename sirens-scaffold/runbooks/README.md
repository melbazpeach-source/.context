# Sirens Runbooks

Operator-facing playbooks. One file per scenario.

| Runbook | Purpose | First written in phase |
|---|---|---|
| `oncall.md` | Pager rotation, escalation paths, SEV definitions | 0 |
| `backup-restore.md` | Snapshot every persistent volume; test restore quarterly | 1 |
| `key-rotation.md` | Rotate API keys, OPENCTI_ADMIN_TOKEN, MISP keys, MinIO creds | 1 |
| `legal-incident.md` | What to do when legal authority changes (subpoena, takedown notice, customer revokes scope) | 0 |
| `feed-poisoning.md` | Quarantine suspect feeds, replay-and-diff against trusted history | 3 |
| `cost-runaway.md` | Stop the bleed when LLM spend exceeds budget; open postmortem | 2 |
| `deception-callback.md` | Triage a canary callback or honeypot interaction end-to-end | 7 |
| `customer-handover.md` | Hand off attribution + recommended actions to a customer SOC | 3 |

Each runbook follows the structure: **Trigger → Severity → Steps → Verification → Postmortem template.**
