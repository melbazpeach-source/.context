# skills/

Vendored skill libraries the swarms load at runtime.

## anthropic-cybersecurity-skills

Submodule of [`mukul975/Anthropic-Cybersecurity-Skills`](https://github.com/mukul975/Anthropic-Cybersecurity-Skills).
754 cybersecurity skills with ATT&CK / NIST-CSF / OWASP mappings.

Shape per skill:

```
skills/<skill-name>/
  SKILL.md          # YAML frontmatter (name, tags, nist_csf, …) + playbook
  scripts/          # executable helpers (optional)
  assets/           # diagrams, sample PCAPs, …
  references/       # links / citations
```

Machine index: `index.json` (name → path + one-line description).
Framework cross-refs: `mappings/{mitre-attack,nist-csf,owasp}/`.

### Consumers

- **Research swarm — Analyst node** (`agents/research/nodes.py:make_analyst`)
  loads skills matching the tasking's detected TTPs (via `mappings/mitre-attack/`),
  feeds the `SKILL.md` body into the narrate prompt, and credits the skill in
  `AgentMessage.provenance`.
- **Detection-Engineering swarm** (future) uses skills in the
  `detection-engineering` subdomain as scaffolds for Sigma/YARA/Nuclei drafts.
- **Hunt swarm** (future) uses skills in the `threat-hunting` subdomain to
  seed hypothesis playbooks.

### Initialising after a fresh clone

```bash
git submodule update --init --recursive sirens-scaffold/skills/anthropic-cybersecurity-skills
```

### Updating

```bash
cd sirens-scaffold/skills/anthropic-cybersecurity-skills
git fetch && git checkout <tag-or-sha>
cd -
git add sirens-scaffold/skills/anthropic-cybersecurity-skills
git commit -m "skills: bump anthropic-cybersecurity-skills to <sha>"
```

Pin to a commit SHA in CI so skill drift doesn't silently change agent
behaviour between runs.
