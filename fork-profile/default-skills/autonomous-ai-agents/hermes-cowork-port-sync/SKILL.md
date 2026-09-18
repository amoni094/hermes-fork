---
name: hermes-cowork-port-sync
description: >
  Use when maintaining port repos that translate the Hermes agent configuration into specifications for other AI assistant platforms. Covers two repos: (1) hermes-to-cowork-port — Cowork/Claude Desktop platform port. (2) hermes-agent-spec — generic AI coding assistant architecture spec (Cursor, Claude Code, Copilot, etc.), no executable code, concept-only. Updates go to the port repo only — never to hermes-config or ~/.hermes/.
version: 2.0.0
triggers:
  - "update the hermes to cowork port"
  - "sync cowork port"
  - "hermes-to-cowork-port"
  - "cowork port git"
  - "portable to cowork"
  - "update the port git"
  - "cowork port out of date"
  - "hermes-agent-spec"
  - "cursor spec"
  - "update cursor port"
  - "sync cursor spec"
related_skills:
  - hermes-config-repo-audit
  - portable-context-layer
---

# Hermes Port Repos

Two repos serve different audiences:

## Repo 1: hermes-to-cowork-port (Cowork / Claude Desktop)

**Repo location:** /var/home/rainbow/hermes-to-cowork-port
**GitHub:** tech-legal/hermes-to-cowork-port
**Constraint:** Updates go to the port repo only. Do NOT touch hermes-config git
or ~/.hermes/.

## Repo 2: hermes-agent-spec (Generic AI Coding Assistant Spec)

**Repo location:** ~/hermes-agent-spec
**GitHub:** tech-legal/hermes-agent-spec (private)
**Purpose:** Conceptual architecture specs so Cursor (or any AI coding assistant)
can understand and re-implement Hermes patterns locally. No executable code, no
API keys. The reader is Cursor itself — specs must be self-contained enough for
an AI to action them directly.
**Structure (11 files, 3320+ lines):**
- README.md — purpose, directory map, quickstart, principles
- architecture/ARCHITECTURE.md — system design, ReAct loop, skill system, Cursor mapping
- memory/MEMORY-SYSTEM.md — 4-layer memory spec, schemas, security
- workflows/AGENT-WORKFLOWS.md — 9 workflow patterns
- skills/SKILLS-CATALOG.md — SKILL.md format spec, 142-skill domain catalog
- tools/TOOLS.md — tool categories, MCP config
- routing/MODEL-ROUTING.md — fallback chain, TALE budget hints
- governance/GOVERNANCE.md — hard blocks, warn rules, operating constraints
- automation/AUTOMATION.md — cron patterns, GitHub Actions templates
- cursor/CURSOR-QUICKSTART.md — zero-to-full setup guide

**Collaborator:** alexeymonin (alexey.monin@nab.com.au) — invited with write access.

**Key design constraint:** Target reader is Cursor's AI agent, not a human.
Every spec section needs a Cursor mapping table: what .cursorrules / .cursor/rules/*.mdc /
MCP server / background agent implements this feature. Dual-frame pattern: "Hermes does X"
+ "Cursor does Y" side-by-side in every major section.

**Sync when:** hermes-config audit changes memory topology, cron jobs, routing, or
veto rules. Update hermes-agent-spec to match since it encodes the same architecture.

---

## What the port repo contains

| Directory/File | Purpose |
|----------------|---------|
| `CLAUDE.md` | Port strategy table + operating rules + model routing |
| `README.md` | Quick-start and directory index |
| `platforms/` | Per-OS setup (linux.md, macos.md, windows.md) |
| `workflows/` | 15+ Cowork task template prompts |
| `scheduled-tasks/` | Hermes cron jobs translated into Cowork Scheduled Task specs |
| `connectors/` | MCP integration map (what works, what doesn't, workarounds) |
| `skills-catalog/` | Full skill index (185 skills, 22 domains) |

---

## Four gap categories to check every sync

### 1. Memory topology (highest drift risk)

CLAUDE.md and connectors/README.md both describe the Hermes memory stack.
They must reflect the authoritative 4-layer topology from docs/memory-topology.md
in hermes-config:

1. Hermes durable memory (MEMORY.md / USER.md) — injected every turn
2. Hindsight (cloud via Anthropic API, text-embedding-3-small 1536d) — long-term structured knowledge
3. Graphiti MCP (Neo4j at localhost:8765) — episodic/relational knowledge graph
4. ~~QMD (flowstate-qmd)~~ — **DISABLED** (`mcp_servers.qmd.enabled: false`); do not port as an active layer. Vault recall → session_search + Hindsight + Obsidian files
   MemPalace MCP — present but disabled

Per-layer Cowork mappings (authoritative — update if the stack changes):
- Layer 1 → Paste MEMORY.md + USER.md into Cowork Global Instructions or a Project's instructions
- Layer 2 → Cowork native Memory (automatic fact retention)
- Layer 3 → No direct equivalent; Cowork Projects approximate it
- Layer 4 → Cowork folder permissions on SecondBrain folder + built-in file search (QMD disabled in source — this is the vault-file fallback, not a QMD port)
- MemPalace → Skip (disabled in source config)

Check: CLAUDE.md port strategy table has a row per memory layer. connectors/README.md
has per-layer detail and per-layer Cowork usage guidance. MCP server table has graphiti
and mempalace rows. Non-portable services table has graphiti and mempalace rows.

### 2. Cron jobs (scheduled-tasks/README.md)

Compare the jobs listed in scheduled-tasks/README.md against the current cron snapshot
in hermes-config (docs/operations-surface-register.md or cron.snapshot.json).

For each job:
- Is the schedule correct? (60m vs 240m vs daily vs weekly)
- Is it documented as portable or non-portable?
- Non-portable jobs (e.g. session-auto-prune — operates on Hermes SQLite) need
  an explicit "not portable" callout with explanation and Cowork workaround.
- New jobs since last sync need a new section (or a "not portable" stub if Cowork
  can't replicate them).

Active job inventory as of 2026-07-03:
1. hourly-hermes-chat-sync — every 240m (not hourly), haiku-4-5, deliver=local
2. obsidian-weekly-review — Fridays 17:00, deliver=local
3. session-auto-prune — every 240m, no-agent, deliver=local — NOT PORTABLE
4–8: check cron.snapshot.json for others

### 3. Provider / model routing (CLAUDE.md, README.md, skills-catalog docs)

Two sub-parts drift independently — check both, not just the fallback chain:

**a) Primary tier table.** This is the higher-drift half. Whenever hermes-config
corrects its routing docs (e.g. discovering the live config is single-tier, not the
multi-tier structure old docs assumed), every port-repo file with a model routing
table needs the same correction — not just CLAUDE.md. On 2026-07-06 the stale
"Sonnet main / Opus delegation / Haiku auxiliary / Fable escalation" 4-tier table
was found duplicated in README.md (two separate tables) and CLAUDE.md (one table),
plus a job description in scheduled-tasks/README.md that still said "haiku-4-5" for
a job that now runs on the main model. Grep the whole repo for stale model name
strings (`sonnet-4-6`, `opus-4-8`, `haiku-4-5`, `fable-5` or whatever the prior
tier names were) rather than editing only the file you expect to be stale.

**b) Fallback chain.** Cerebras→SambaNova→Mistral must be noted as a reference,
with an explicit callout that Cowork is Anthropic-only and has no multi-provider
fallback. Re-check the SambaNova model name specifically — it has changed versions
before (DeepSeek-V3.1 → DeepSeek-V3.2) without the chain structure changing, so a
stale version string can hide for a while.

Active fallback chain as of 2026-08-25: Cerebras (gpt-oss-120b) → SambaNova (DeepSeek-V3.2) → Mistral (mistral-large-latest) — continuity only; Cerebras quota-exhausted and SambaNova rate-limited, so this currently lands on Mistral large.
Active primary as of 2026-09-09: session parent `claude-sonnet-4-6` / anthropic. Fallback + `delegation.model` are `grok-4.6` / xai. Aux leaves `mistral-small-latest` / mistral. `cerebras/zai-glm-4.7` is archived — do not use. opus-4-8 / haiku-4-5 / fable-5 exist and are callable but override-only, never auto-routed. Canonical: `claude-routing-hierarchy`. Re-read live `~/.hermes/config.yaml` every sync — do not copy this snapshot.

### 4. README.md directory index counts

When jobs or files are added, update the count/description in the README What's here table.
e.g. "6 Hermes cron jobs" vs "8 Hermes cron jobs".

---

## Procedure

1. **Read the hermes-config audit docs** (source of truth):
   - `/var/home/rainbow/hermes-config/docs/memory-topology.md`
   - `/var/home/rainbow/hermes-config/docs/operations-surface-register.md`
   - `/var/home/rainbow/hermes-config/cron.snapshot.json`
   - `/var/home/rainbow/hermes-config/docs/current-workflow.md` (fallback chain)

2. **Read the port repo docs** (what needs updating):
   - `/var/home/rainbow/hermes-to-cowork-port/CLAUDE.md`
   - `/var/home/rainbow/hermes-to-cowork-port/README.md`
   - `/var/home/rainbow/hermes-to-cowork-port/connectors/README.md`
   - `/var/home/rainbow/hermes-to-cowork-port/scheduled-tasks/README.md`

3. **Compile gap list** — for each of the 4 categories, state what differs before writing anything.

4. **Patch the port repo** — targeted patches only (use patch tool, not write_file overwrite):
   - CLAUDE.md: port strategy table rows, memory description, fallback chain note
   - README.md: job counts, memory description
   - connectors/README.md: memory section, MCP server table, non-portable table
   - scheduled-tasks/README.md: schedule values, job sections for new/non-portable jobs

5. **Commit with clear message**:
   ```
   git add -A && git commit -m "Sync with hermes-config audit <date>: <summary>

   Changes:
   - CLAUDE.md: <what changed>
   - README.md: <what changed>
   - connectors/README.md: <what changed>
   - scheduled-tasks/README.md: <what changed>"
   ```

6. **Push**:
   ```
   cd /var/home/rainbow/hermes-to-cowork-port && git push
   ```

---

## Cowork platform portability map (reference)

| Hermes feature | Cowork equivalent | Portable? |
|----------------|------------------|-----------|
| Durable memory (MEMORY.md/USER.md) | Paste into Global Instructions or Project instructions | Yes |
| Hindsight (cloud, text-embedding-3-small) | Cowork native Memory | Approximate |
| Graphiti MCP (Neo4j knowledge graph) | No equivalent — Cowork Projects approximate | No |
| QMD / Obsidian vault search | Disabled in source (`enabled: false`) — skip; vault files via SecondBrain folder perms | N/A |
| MemPalace MCP | Disabled in source — skip | N/A |
| Skills library | Paste workflow templates as task prompts | Partial |
| Cron jobs | Cowork Scheduled Tasks | Partial |
| delegate_task subagents | Cowork parallel task execution | Approximate |
| terminal backend | Computer Use (macOS/Windows only; unavailable Linux) | Platform-limited |
| session_search | Cowork Projects / Tasks list | Approximate |
| Firecrawl self-host | Cowork built-in web search | Approximate |
| SearXNG local | Cowork built-in web search | Approximate |
| Ollama local models | Not available — Cowork is Anthropic-only | No |
| Hermes fallback chain (Cerebras/SambaNova/Mistral) | Not available — Cowork is Anthropic-only | No |
| session-auto-prune cron | Not portable — Hermes SQLite-specific | No |
| Graphiti cron / MCP jobs | Not portable — local Neo4j-specific | No |

---

## README.md — comprehensive documentation refresh for the port repo

The port repo README serves a different purpose than hermes-config's README. It is a
**translation guide**, not a technical reference. Every section must answer two questions:
"how does Hermes do this?" and "what is the Cowork equivalent?"

### Dual-frame pattern (required for a full README refresh)
Every major section in the port README needs both frames side-by-side:
- A brief explanation of how Hermes implements the capability
- An explicit "Cowork equivalent" column, table row, or note
- Where there is no equivalent: explicit "No direct equivalent" with the nearest workaround

### Sections that require the dual-frame treatment
| Section | Hermes frame | Cowork frame |
|---------|-------------|--------------|
| Soul / Persona | What SOUL.md says and why it's minimal | Paste into Global Instructions |
| Skills Management | Lifecycle, domain families, disabled count | Workflow templates in workflows/ dir |
| Memory Topology | 4-layer stack with backend + scope | Layer-by-layer Cowork mapping table |
| LLM Routing | Primary chain + fallback + capability matrix | Cowork is Anthropic-only; no fallback |
| Workflow Patterns | Single-agent, delegate_task, cron, Ouroboros | Cowork parallel subtasks, Scheduled Tasks |
| Self-Optimization | Skill patching, memory hygiene, upgrade passes | Cowork maintenance habits equivalent |
| Security Posture | Veto layer, hard blocks, secret hygiene | Cowork Global Instructions rules equivalent |

### Portability notes (always at the end)
After all sections, list capabilities that have NO Cowork equivalent and why:
- Local service calls (Firecrawl, SearXNG) — use Cowork built-in web access
- Sub-hourly cron schedules — Cowork minimum is hourly
- Multi-provider fallback chain — Cowork is Anthropic-only
- Pre-tool veto governance — behavioral rules only, not technical intercepts
- Computer use on Linux — unavailable
- Local embedding (Ollama) — removed (Ollama uninstalled Jul 2026); Hindsight now uses OpenAI text-embedding-3-small via Anthropic API; Cowork Memory is automatic and cloud-based
- Graphiti knowledge graph — no equivalent

### Source material order for a port README refresh
Read these in order (batch reads, then write):
1. `SOUL.md` — persona
2. `hermes-config/docs/memory-topology.md` — memory stack (authoritative)
3. `hermes-config/docs/routing-and-workflow.md` — LLM routing
4. `hermes-config/docs/current-workflow.md` — cron jobs, runtime state
5. `hermes-config/docs/upgrade-pass-*.md` — security posture
6. `hermes-config/veto/rules/hermes-hard-blocks.yaml` — what is hard-blocked
7. `hermes-to-cowork-port/CLAUDE.md` — existing port strategy table

---

## Pitfalls

- **Schedule values drift in hermes-config without port repo update** — e.g. "hourly" was
  actually 240m; always re-read the cron snapshot before accepting the port's numbers.
- **New cron jobs appear in hermes-config without port counterparts** — session-auto-prune
  and obsidian-weekly-review were both missing from the port repo until caught by audit.
  Check job count each sync.
- **Non-portable jobs need explicit callouts, not silence** — if a job can't be replicated
  in Cowork, add a section explaining why and what the nearest Cowork workaround is.
  Absence of the job in the port docs creates a false impression it doesn't exist.
- **Memory topology is the highest-drift section** — the 4-layer stack and per-layer
  Cowork mappings appear in multiple files (CLAUDE.md, connectors/README.md, README.md).
  All must be updated together when the stack changes.
- **Graphiti and MemPalace must appear in three places** — MCP server table, non-portable
  services table, and the memory topology mapping. Missing from any one is a partial gap.
- **Do not use write_file to overwrite connectors/README.md or scheduled-tasks/README.md**
  — they are long; use targeted patch calls to avoid clobbering unchanged content.
- **README count line** — "6 cron jobs" / "8 cron jobs" in the What's here table drifts
  silently when jobs are added. Always check the number matches actual scheduled-tasks sections.
- **Port repo remote moved** — on push you may see
  "remote: This repository moved. Please use the new location: ..."
  This is informational only; the push succeeds. Not an error. (As of 2026-07-06
  the new canonical location is `tech-legal/hermes-to-cowork-port`; consider
  updating `git remote set-url origin` once, rather than tolerating the redirect
  indefinitely.)
- **Multi-patch edits can leave dangling fragments** — if a file has been partially
  edited across sessions (e.g. a table row replaced but a trailing sentence from
  the old paragraph left behind), a table-row-scoped patch can miss it. After
  patching a routing/model table, re-read the surrounding ~15 lines to check for
  an orphaned sentence fragment that no longer connects to anything above it.
- **hermes-agent-spec phantom directory map** — When building the hermes-agent-spec repo
  using parallel subagents, subagent task 1 (README writer) planned an aspirational
  multi-file directory structure and wrote it into the README directory map — 22 files
  that didn't exist. The actual repo used a single-file-per-directory layout. The README
  directory map was wrong from day one. **Fix pattern**: After any parallel subagent build,
  read the README directory map and verify every listed path against `find . -type f`.
  Fix before first commit. Never let a subagent write a directory map without validating
  the actual file tree first.

- **Collaborator invite: personal repo vs org repo** — GitHub's REST API for repo
  collaborator invites uses different mechanisms by repo owner type:
  - Personal repos (`/repos/USER/REPO/collaborators/USERNAME`): requires GitHub **username** only.
    Email-based invite fails with 404.
  - Org repos: can use either username (repo-level) or email (org-level via `/orgs/ORG/invitations`).
    Org-level email invite requires `admin:org` token scope.
  **Worked pattern**: transferred the new personal repo to the existing `tech-legal` org,
  then used repo-level collaborator invite by guessed username (`alexeymonin`).
  Username lookup: `gh api users/<guess> --jq '.login,.name'` — try firstname+lastname
  combinations until you get a hit.
  See `references/sync-2026-07-18.md` for full process.

- **Subagent parallel-write conflict** — When 3 subagents write files concurrently
  AND the parent agent also writes to the same paths, last write wins silently.
  In this session: subagents wrote 730-line MEMORY-SYSTEM.md and 765-line AGENT-WORKFLOWS.md,
  then parent wrote shorter versions, then subagents' timing meant the committed versions
  were actually the subagent ones (730/765 lines). The parent's versions of ARCHITECTURE.md
  (284 lines) won over the subagent's 972-line version. Net: inconsistent quality across files.
  **Fix**: assign non-overlapping file ownership before dispatching. Either parent writes
  all files and subagents are read-only, OR subagents own specific named files and parent
  stays out of those paths. Never let both parent and subagents write to the same files.

---

## References

See `references/sync-2026-07-03.md` for the first full sync run: all gaps found,
files patched, commit hash d8d4f90.

See `references/sync-2026-07-06.md` for the model-routing-table sync: found and
fixed a stale 4-tier routing table (README.md x2, CLAUDE.md, scheduled-tasks/README.md),
commit hash 868ce7e.

See `references/sync-2026-07-18.md` for hermes-agent-spec creation: new generic AI
coding assistant spec repo, adversarial review pass (7 HIGH + 5 MEDIUM fixes),
collaborator invite process, parallel-write conflict pitfall.
- `references/example-hermes-cowork-port-2026.md` — Example: Adversarial Review — Hermes → Cowork Port (2026)
- `references/workflow-chain-audit-aug2026.md` — Cross-Category Workflow Chain Audit — August 2026
