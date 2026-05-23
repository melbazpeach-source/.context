# rules/

Vendored detection-rule artifacts the Hunt and Detection-Engineering
swarms read from (and, eventually, write drafts into).

**Not to be confused with `skills/`** — skills are LLM reasoning
scaffolds (playbooks + ATT&CK mappings), rules are the things the hunter
actually executes against telemetry.

## sigma

Submodule of [`SigmaHQ/sigma`](https://github.com/SigmaHQ/sigma). ~4k
rules across:

| Directory | Contents |
|---|---|
| `rules/` | Core SigmaHQ rule library |
| `rules-dfir/` | DFIR-specific rules (memory, file-system, registry) |
| `rules-emerging-threats/` | Threat-group / campaign rules |
| `rules-threat-hunting/` | Hypothesis-driven hunting rules |
| `rules-compliance/` | Compliance-framework mappings |
| `rules-placeholder/` | Rules with `<REPLACE_ME>` tokens to tune per env |
| `deprecated/` | Retired rules — **do not load** |
| `unsupported/` | Rules for unsupported backends — **do not load** |

### Consumer (Phase 4.1)

`agents/hunt/dispatch.py:LiveDispatch.write_queries` will:

1. Look up candidate rule files by `Hypothesis.ttp` (via Sigma's
   `tags: attack.t1566` frontmatter).
2. Load the YAML, call `pysigma` + `pysigma-backend-opensearch` to
   translate to a Wazuh-indexable OpenSearch DSL query.
3. Emit one `SigmaQuery` per loaded rule.

### Initialising after a fresh clone

```bash
git submodule update --init --recursive sirens-scaffold/rules/sigma
```

### Updating

```bash
cd sirens-scaffold/rules/sigma
git fetch && git checkout <tag-or-sha>
cd -
git add sirens-scaffold/rules/sigma
git commit -m "rules: bump SigmaHQ/sigma to <sha>"
```

Pin to a SHA in CI. Sigma rules change frequently and a silent pull
would drift agent behaviour between runs.

## Not yet vendored (future)

- `yara/` — candidate sources: Elastic's [protections-artifacts](https://github.com/elastic/protections-artifacts),
  Neo23x0/signature-base, YARA-Forge. Pick one after the
  Detection-Engineering swarm lands.
- `nuclei/` — ProjectDiscovery [nuclei-templates](https://github.com/projectdiscovery/nuclei-templates),
  including the 1496 KEV-tagged templates called out in the survey.

When added, follow the same layout: one submodule per rule family under
`rules/<family>/`, pinned to a SHA.
