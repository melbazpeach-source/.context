# Sirens — Ethics & Legal Policy

> **Status:** Draft. Must be reviewed by counsel before any code in
> `agents/` or `mcp-servers/` is run against live targets.

## Mission

Sirens exists to **defend**: detect, attribute, and disrupt malicious activity
against systems and people we are authorized to protect. It does not exist to
attack, retaliate, or build offensive capability.

## Hard "MUST NOT" rules

These are non-negotiable and apply to every agent in every swarm.

1. **No unauthorized access.** Sirens never bypasses authentication, exploits
   vulnerabilities, or otherwise gains entry to systems it is not authorized
   to access. (CFAA / CMA / NIS2 / equivalent local statute.)
2. **No use of leaked credentials.** Even when a credential is publicly
   posted, Sirens does not authenticate with it. Credentials are observables,
   not tools.
3. **No ToS-violating scraping.** Sirens uses official APIs with
   authentication and rate limits. Where no API exists, Sirens reads only
   what is reachable without ToS breach (robots.txt honored, public pages,
   official syndication feeds).
4. **No outbound interaction with attacker infrastructure.** Sirens is
   passive against attacker-controlled systems. No scans, probes, takedowns,
   uploads, message-board posts, or callbacks against attacker infra.
5. **No PII harvesting beyond the minimum needed for an attribution claim.**
   Personal identifiers are aggregated to actor or campaign context, not
   retained per-individual without explicit purpose.
6. **No detection-evasion tradecraft.** Sirens does not develop,
   document, or deploy techniques whose primary purpose is evading
   defensive products.

## Authorization matrix

| Capability | Authorization required |
|---|---|
| Reading public OSINT (abuse.ch, OTX, NVD, CISA KEV, etc.) | None beyond compliance with each source's ToS |
| Querying paid feeds with our keys (VirusTotal, Shodan, etc.) | Vendor agreement on file |
| Running Wazuh / Velociraptor against our endpoints | Standing internal authorization in scope allow-list |
| Deploying canary tokens in our environments | Standing internal authorization |
| Operating honeypots on our infra | Standing internal authorization + DPIA |
| DNS sinkholing of a domain | Domain title (we own it) **or** registrar/court order **or** CERT/LEA partnership |
| Any decoy interaction reaching past our network edge | Written authorization, per engagement |
| Sharing TLP:AMBER+ artifacts externally | Approved sharing community + need-to-know |

If the table above does not list a capability, the default is **forbidden
until added with sign-off**.

## Data minimization

- Collect only what supports a current, declared tasking.
- Retain raw collector output for ≤ 90 days; retain aggregated graph state
  indefinitely with reviewable provenance.
- Allow purge requests against the graph (subject identifier, retention
  override).

## Disclosure & sharing

- Findings about third parties: TLP'd appropriately; default TLP:AMBER.
- Vulnerabilities discovered incidentally during research: responsibly
  disclosed to the affected party before any public mention.
- Findings about own customers (if applicable): private to the customer until
  they consent to sharing.

## Cross-references

- `docs/scope-allowlist.template.yaml` — the per-engagement contract that
  binds the rules above to specific targets and time windows.
- `.context/research/sirens-swarm-survey.md` §5 — the active-tracking layer
  and the hard line.
- `schemas/tasking.py` — the `Authorization` and `Posture` fields the
  supervisor enforces at runtime.
