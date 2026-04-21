# Vendored MCP servers

Four upstream MCP servers we use as-is (no fork). Vendored via `git submodule`
during Phase 2 bring-up:

```bash
cd sirens
git submodule add https://github.com/gbrigandi/mcp-server-wazuh   mcp-servers/vendored/wazuh
git submodule add https://github.com/gbrigandi/mcp-server-cortex  mcp-servers/vendored/cortex
git submodule add https://github.com/gbrigandi/mcp-server-misp    mcp-servers/vendored/misp
git submodule add https://github.com/gbrigandi/mcp-server-thehive mcp-servers/vendored/thehive
git submodule update --init --recursive
```

Each upstream ships its own Dockerfile; compose overlays in `compose/` build
and run them. Pin the submodule SHA explicitly in `compose/docker-compose.mcp.yml`
(via `build: context:` pointing at the submodule path) so we don't track a
moving target.

## When to bump

- Upstream tags a release.
- A CVE is disclosed against a vendored server.
- A new tool we need lands upstream.

Process: check out the new tag on the submodule, run the full Phase 2 golden-path
test, then commit the submodule SHA bump separately from any application changes.

## When to fork

Do not fork unless: (a) we need a tool upstream refuses to add, AND (b) the
change is too large for an upstream PR. If we fork, mirror the repo under
`melbazpeach-source/` and update the submodule URL — do not carry a local-only
fork.
