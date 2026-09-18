# MCP Server Routing Consistency Check
# Added: August 2026 — from adversarial audit of hermes-memory-surface-selection

## The Problem

Skills that list retrieval surfaces (like `hermes-memory-surface-selection`) enumerate
MCP servers in a decision-order table. If an MCP server is later disabled in config.yaml,
the skill's routing table becomes stale — agents call tools that silently fail.

## Confirmed Instance (August 2026)

`hermes-memory-surface-selection` listed `qmd (mcp_qmd_*)` as retrieval surface #3.
Config had `qmd: enabled: false`. The skill also said "MemPalace is disabled; use qmd
instead" — meaning BOTH fallback surfaces were disabled, and the decision table gave
no usable path for local note retrieval.

Fix applied: struck through qmd in the routing table, redirected to session_search +
Hindsight, updated the "Use qmd for" section to "qmd disabled — fallback to
session_search + Hindsight".

## Check Command

Run at start of every consolidation audit pass:

```bash
grep -A3 'qmd:\|mempalace:\|graphiti:\|stealth-browser-mcp:' ~/.hermes/config.yaml | grep -E 'enabled|command'
```

For each server showing `enabled: false`, search the skill library for references to
its tools:

```bash
grep -r 'mcp_qmd\|qmd_\|mempalace\|mcp_mempalace' ~/.hermes/skills/ --include='*.md' -l
```

Each hit is a candidate for a routing-table update.

## General Rule

Every retrieval surface decision table in any skill MUST be verifiable against live
config before the audit pass closes. This is now a mandatory Step 4b check (runs
alongside the config/cron consistency surface, not as a separate pass).

## Adversarial Audit Table Row

Add to the Step B cross-check table in `agent-memory-consolidation`'s Adversarial
Topology Audit section (note: agent-memory-consolidation is user-owned — recommend
`hermes curator adopt agent-memory-consolidation` to enable future patches):

| HIGH | Skill routes to disabled MCP server | A skill's retrieval decision table lists an MCP server (`qmd`, `mempalace`) that is `enabled: false` in config.yaml. Calls silently fail. Cross-check: `grep -A3 'qmd:\|mempalace:' ~/.hermes/config.yaml \| grep enabled`. Strike through disabled servers and redirect to next fallback. |
