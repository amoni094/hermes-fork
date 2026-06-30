# MemPalace as a Hermes MCP integration example

## Recommendation
Adopt MemPalace as an optional MCP-backed adjunct memory/retrieval surface, not as a replacement for Hermes durable memory or context compaction.

## Why it fit
- It already exposes an MCP server entrypoint.
- It adds useful retrieval/graph-style tooling without invasive Hermes-core changes.
- The integration is reversible and cheap to verify.

## Upstream signals that mattered
- `pyproject.toml` exposes:
  - `mempalace = "mempalace.cli:main"`
  - `mempalace-mcp = "mempalace.mcp_server:main"`
- `uvx --from mempalace mempalace-mcp --help` worked locally.

## Hermes-side implementation pattern
1. Add a launcher script at `~/.hermes/scripts/mempalace-mcp.sh`:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   exec uvx --from mempalace mempalace-mcp "$@"
   ```
2. Point Hermes MCP config at that script.
3. Verify with:
   - `hermes mcp list`
   - `hermes mcp test mempalace`

## Why the launcher script was the right fallback
The direct `hermes mcp add ... --args` path was awkward for passing `uvx --from ...` cleanly. A wrapper script produced a stable command path and simpler config.

## Hermes source change pattern
If you want first-class CLI support, add a preset in `hermes_cli/mcp_config.py` and cover it with a targeted test in `tests/hermes_cli/test_mcp_config.py`.

Preset shape used here:
- command: `uvx`
- args: `["--from", "mempalace", "mempalace-mcp"]`

## Verification outcome from this session
- `hermes mcp test mempalace` connected successfully
- 30 tools were discovered
- targeted MCP config tests passed after running the file with project addopts disabled

## Scope lesson
For external memory systems, prefer:
- Hermes built-in memory for agent/user durable facts
- external MCP memory systems for optional retrieval/workspace augmentation

That separation keeps Hermes behavior stable while still enabling richer external memory tools.
