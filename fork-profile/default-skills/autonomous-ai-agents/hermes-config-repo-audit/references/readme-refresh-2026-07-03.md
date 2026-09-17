# README Comprehensive Refresh — 2026-07-03

This reference captures the content structure and framing used in the first full explanatory
README refresh for both hermes-config and hermes-to-cowork-port.

## hermes-config README

Final size: 341 lines. Sections in order:

1. What's here (file index)
2. Documentation (docs/) index
3. Soul / Persona Configuration
   - Key content: SOUL.md is 50 words, intentionally minimal. Voice only; rules elsewhere.
   - Design rationale: fewer injected tokens per session; behavioral rules in AGENTS.md + veto.
4. Skills Management
   - Inventory: ~185 skills, 22 domains, ~122 enabled, ~63 disabled
   - Lifecycle table: author → load → patch → disable → delete → guard
   - Optimization note: 63 skills disabled (macOS-only, missing deps, stale + zero use count)
   - Domain families table: 8 rows covering major categories
5. Memory System — Topology and Routing
   - 6-row layer table: Hermes durable / Hindsight / Graphiti / QMD / Session search / MemPalace
   - Columns: Layer, Backend, Scope, When to use
   - Routing rules summary: 6 bullets, one per layer
   - Embedding backend: Ollama localhost:11434, models qwen3:8b + llama3.2:3b
6. LLM Routing
   - Primary chain: 4 rows (Sonnet/Opus/Haiku/Fable-5) with escalation discipline
   - Fallback chain: 3 providers in order
   - Capability-based routing: 6 heuristic bullets (context size, latency, privacy, offline)
   - Context compression: enabled at 0.5 threshold, Haiku auxiliary
7. Workflow Patterns
   - Single-agent (default)
   - delegate_task: when to use, config (Opus 4.8, max 3 children, depth 1)
   - Cron: 8-job table with schedule + purpose
   - Role-based pipelines: fan-out / fan-in pattern
   - Ouroboros: trigger conditions + 5-stage workflow
   - Adaptive routing table: 6 complexity tiers × routing decision
8. Self-Optimization and Maintenance Patterns
   - 4 subsections: skill improvement, memory hygiene, cron hygiene, config evolution + upgrade passes
9. Security Posture
   - Pre-tool veto: hard blocks (listed by category) + warn tier
   - Destructive command approvals: disabled + allowlist
   - Secret hygiene: .env exclusion, sanitizer script, WhatsApp wildcard commented out
   - Messaging consent: skill reference
   - Network exposure: local-only MCP, local SearXNG/Firecrawl, inbound-only gateway
   - Data training: provider selection discipline
   - Repo export hygiene: exclusions list
10. Important exclusions from repo export

## hermes-to-cowork-port README

Final size: 348 lines. Same 10 thematic sections but with dual-frame treatment throughout.

Key structural difference from hermes-config README:
- Every section has an explicit "Cowork equivalent" column or note
- Model routing section explicitly states "Cowork is Anthropic-only; no multi-provider fallback"
- Cron section is a mapping table (Hermes job → schedule → Cowork equivalent) with notes on
  non-portable jobs (sub-hourly) and Cowork minimum cadence (hourly)
- Security section describes Cowork Global Instructions as the behavioral-rules equivalent
  to the veto layer, with explicit note that it is not a technical intercept
- Portability notes section at end: 9 capability gaps with no Cowork equivalent

## Efficient workflow

Batch all source reads before writing anything:
- hermes-config: SOUL.md, memory-topology.md, routing-and-workflow.md,
  current-workflow.md, upgrade-pass-*.md, veto/rules/hermes-hard-blocks.yaml,
  cron.snapshot.json
- cowork-port: CLAUDE.md (for existing port strategy table)

Then write both files in a single pass each (write_file, not patch — these are
full replacements when doing a comprehensive refresh).

Verify section headers with `grep '^## '` after writing.
