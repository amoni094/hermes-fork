---
name: hermes-mcp-integration
description: Integrate third-party MCP servers into Hermes with low-risk verification, launcher-script fallbacks, and optional CLI preset/test updates.
---

# Hermes MCP integration

Use this when you need to evaluate, install, verify, or upstream support for an external MCP server in Hermes Agent.

## When to use
- A user wants Hermes to use a third-party MCP server.
- You are evaluating whether a tool should be integrated versus copied into Hermes core.
- You need to add or verify a Hermes CLI `mcp` preset for a commonly used server.
- The MCP server is packaged for `uvx`, `npx`, or another launcher and needs a stable Hermes entrypoint.

## Default stance
Prefer integrating external capability as an MCP server first.
Do not merge it into Hermes core memory, compression, or agent logic unless there is a clear product reason that MCP cannot satisfy.

For memory-oriented systems, default to treating them as adjunct retrieval surfaces unless they truly need to become a native Hermes memory provider. Keep Hermes built-in durable memory semantics small and stable; use MCP for broader external/project/archive retrieval.

## Steps
1. Inspect the upstream project for:
   - an MCP server entrypoint
   - packaging/install command
   - transport expectations (stdio/http)
   - auth/env requirements
2. Decide the smallest viable Hermes integration:
   - direct `hermes mcp add ...` if the command shape fits cleanly
   - otherwise a local launcher script under `~/.hermes/scripts/` that `exec`s the real command
3. Add the server to Hermes using the CLI flow when possible.
4. Verify with `hermes mcp list` and `hermes mcp test <name>`.
5. If the integration is likely reusable, add or patch a Hermes CLI preset and add targeted tests.
6. Keep the integration reversible: minimal config, no invasive core changes unless justified.

## Launcher-script pattern
Use a wrapper script when Hermes needs a single stable executable path or when argument passthrough is awkward.

Example shape:
```bash
#!/usr/bin/env bash
set -euo pipefail
exec uvx --from <package> <entrypoint> "$@"
```

Why this helps:
- gives Hermes a clean `command:` path
- avoids brittle quoting/argument parsing in CLI setup flows
- makes local verification and later replacement easy

## Verification checklist
- The upstream MCP entrypoint runs with `--help` or equivalent.
- `hermes mcp add` saves the server successfully.
- `hermes mcp list` shows it enabled.
- `hermes mcp test <name>` connects and discovers tools.
- If Hermes source was changed, run the smallest targeted test file that covers the changed preset/config path.

## When to upstream a preset
Add a built-in preset when all are true:
- the server is generally useful beyond one machine
- startup command is stable and concise
- the install path is not user-secret-dependent
- a small test can lock in the command expansion

## References
- `references/browser-stealth-firecrawl-integration.md` — concise notes for pairing a stealth browser MCP with local/self-hosted Firecrawl, including Flatpak/PATH shim and verification sequence.

## Pitfalls
- Do not treat a valuable external memory/retrieval system as a forced replacement for Hermes built-ins; MCP is often the right boundary.
- If direct CLI `--args` passthrough is awkward, switch quickly to a launcher script instead of fighting shell parsing.
- Do not claim success until `hermes mcp test` has actually connected and enumerated tools.
- Prefer targeted tests over broad suites when changing MCP config/preset code.
- For browser-stealth / anti-bot integrations that must complement Firecrawl, prefer a repo that is already an MCP server over a custom browser/fork that still needs glue code. Integration fit beats stronger-sounding fingerprint claims if the latter does not drop cleanly into Hermes.
- On Silverblue/Flatpak-heavy systems, if a browser MCP expects `chromium` or `google-chrome` on PATH, a durable fix is a small shim in `~/.local/bin/` that execs `flatpak run org.chromium.Chromium "$@"`, then have the MCP launcher script export that PATH before starting the server.
- When pairing a browser MCP with self-hosted Firecrawl, complete both halves of the integration: register/test the MCP, set `web.extract_backend` to `firecrawl`, and point `FIRECRAWL_API_URL` at the local instance. Verify all three: Firecrawl HTTP reachability, `hermes mcp test`, and one real browser smoke test (spawn -> navigate -> close).
- When a user says "implement this repo" and the upstream project includes Hermes-facing packaging (skill/plugin/MCP) plus broader methodology docs, do a packaging triage first: identify whether the Hermes deliverable is actually a local skill install, an MCP server, or a deeper code integration. Read the repo's Hermes installer/entrypoint and the methodology source-of-truth docs before making changes.
- If the repo's Hermes integration is skill-only, prefer the smallest reversible path: clone locally, inspect the installer, install into `~/.hermes/skills/`, and verify discoverability with `hermes skills list` before claiming implementation. Do not overbuild a custom integration when the upstream deliverable is already a skill.

## Support files
- `references/mempalace.md` — concrete example of evaluating and integrating MemPalace as a Hermes MCP server.
- Related skill: `hermes-memory-surface-selection` — use when deciding whether retrieved information belongs in Hermes durable memory, session history, qmd, or MemPalace.

## Output expectations
Report:
- whether the project is worth integrating
- whether integration should be MCP-only or deeper
- exact files changed
- exact verification commands and outcomes
- any reversible follow-up options
