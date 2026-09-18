# Runtime Architecture Audit — 2026-08-14

Full cross-layer audit of the live `~/.hermes/` environment. Findings cross-checked
against config.yaml, cron/jobs.json (13 jobs), all scripts in `~/.hermes/scripts/`,
plugin directory, and Hermes source internals.

---

## CRITICAL Findings

### C-1: l1-promote races l1-extract — pipeline ordering broken
**Files:** `cron/jobs.json` — both `l1-extract-periodic` and `l1-promote-periodic`  
Both jobs share schedule `interval: 180 minutes`. Their `next_run_at` timestamps differ
by **3.94 seconds** only (determined by creation-time offset at 2026-07-09T19:28:37 vs
19:28:41). Any scheduler jitter, slow extract run, or restart destroys ordering.  
- l1-extract `last_run`: `2026-08-13T21:54:01.857575+10:00`
- l1-promote `last_run`: `2026-08-13T21:54:05.800460+10:00` (4 seconds after)
**Risk:** Promote runs before extract writes new facts → stale promotion cycle.  
**Fix direction:** Give downstream job a longer interval (e.g. 210m) OR add a lock/dependency.

### C-2: stealth-browser-mcp args is a JSON string, not a YAML list
**File:** `config.yaml`, key `mcp_servers.stealth-browser-mcp.args`  
Stored as `'["/var/home/rainbow/.hermes/mcp/stealth-browser-mcp/src/server.py"]'` (a
Python string). `mcp_config.py` line 240 does `cmd_args = list(preset.get("args") or [])`.
`list()` on a string yields individual characters, not the intended arg list.  
- Runtime confirmation: `type(args) = <class 'str'>`, value is the full JSON string.
- The shell script (`stealth-browser-mcp.sh`) works correctly (hardcoded args + `--minimal`).
- The MCP config-driven spawn path is broken — if Hermes ever restarts and respawns from
  config rather than the shell script, the server will receive malformed args.  
**Fix direction:** Change `args` field in config to proper YAML list: `- /path/to/server.py`

---

## HIGH Findings

### H-1: l1-extract.py script comment contradicts cron config
**File:** `scripts/l1-extract.py` line 28: `no_agent=False, every 30m`  
**Live cron:** `no_agent=True, every 180m`  
The script was written assuming agent invocation (may use tool calls) but runs as a
standalone script without agent context. Schedule is 6× slower than header implies.

### H-2: hermes-memory-drift-audit.py output silently discarded
**File:** `cron/jobs.json` job `3170e542c493`, output dir `cron/output/3170e542c493/`  
`no_agent=True` daily drift audit writes output to `cron/output/<job-id>/YYYY-MM-DD.md`.
No downstream watcher reads that directory. `hermes-mutation-gate-watch.sh` watches a
**different** path (`integrations/hermes-agent-self-evolution/output/`).  
Confirmed: 2026-08-13 run produced `Status: silent (empty output)` — meaning output was
empty that day, but any future findings would also be silently discarded.

### H-3: 7 scripts with no cron job or plugin wiring (orphaned utilities)
All exist on disk but have no cron entry and no config reference:
- `canvas-offload.py` — manual-only Mermaid canvas offload utility
- `focus_compress.py` — context compression utility (manual or agent-invoked)
- `hermes-hud.py` — status HUD display, manual
- `memory-staleness.py` — staleness detection (has been run once via cron narrative, no dedicated job)
- `skill-graph-walk.py` — GoS dependency walker, manual
- `issue-to-agents.py` — GitHub issue → agent fan-out, manual
- `adversarial_quarantine_review.py` — adversarial review script, manual

### H-4: skill-prune-audit has never run (last_status=None)
**File:** `cron/jobs.json`, job `skill-prune-audit`, schedule `0 9 1 * *`  
`last_status: None` — never executed. The `skill_prune_audit.py` script is solid
(AutoRefine-based, arXiv:2601.22758). With 170+ skills, a 60-day-window prune+merge
scan has never fired. Likely missed Aug 1 trigger if job was added after that date.

### H-5: agent.api_max_retries=1 (below default of 3)
**File:** `config.yaml`, key `agent.api_max_retries`  
Default per source (`cron/scheduler.py` line 1879): 3. Set to 1 means a single transient
API error (overload 529, network blip) fails the entire agent turn with no retry. Given
Anthropic-API-only inference with no local fallback, this is fragile for cron jobs.

---

## MEDIUM Findings

### M-1: Memory pipeline total lag = up to 10h
l1-extract (180m interval) → l1-promote (180m, same schedule, +4s offset) →
l1-hindsight-promote (4h offset: last run `2026-08-13T23:56:30` vs extract `21:54:01`).
A fact from a session can take up to 10h to surface in Hindsight-backed memory.

### M-2: MOA preset references OpenAI (gpt-5.5) with no OpenAI provider configured
**File:** `config.yaml`, `moa.presets.default.reference_models[0]`  
`provider: openai, model: gpt-5.5`. No OpenAI provider in `custom_providers` or
`fallback_providers`. If MOA is enabled without adding OpenAI credentials, it fails
immediately. Protected now by `enabled: false` in the preset.

### M-3: obsidian-weekly-review has BOTH script AND prompt fields (unusual dual config)
**File:** `cron/jobs.json`, job `bcb9c8082d9c`  
`no_agent: false`, has both `script` and `prompt`. Behavior when both are set may be
undefined depending on the scheduler's handling. Skills required: `['hermes-obsidian-sync', 'obsidian']` — both confirmed present and not in `skills.disabled`.

### M-4: groq-split-tunnel.sh is an orphaned script (Groq not configured)
**File:** `scripts/groq-split-tunnel.sh`  
No Groq provider in config. No cron entry. Script exists but serves no active purpose.

### M-5: mempalace-mcp.sh — MCP server disabled in config
**File:** `config.yaml`, `mcp_servers.mempalace.enabled: false`  
Script exists but the MCP server is disabled. Shell script is unreachable from config-driven spawn.

### M-6: qmd-local.sh — QMD MCP disabled in config
Same pattern as M-5. Script exists, server disabled.

### M-7: kanban toolset in platform_toolsets.cli but no kanban plugin enabled
**File:** `config.yaml` line ~317, `plugins.enabled: [orca-status]` only  
`kanban-orchestrator` and `kanban-worker` skills are disabled. Requesting the `kanban`
toolset in a session finds no backing tools.

### M-8: image_gen and spotify in known_plugin_toolsets but neither plugin enabled
**File:** `config.yaml`, `known_plugin_toolsets.cli`  
Neither `image_gen` nor `spotify` plugin appears in `plugins.enabled`.

### M-9: session-auto-prune runs every 240m, not "hourly"
**File:** `cron/jobs.json`, job `1ea1d2459f51`  
Name is `session-auto-prune`; schedule is `every 240m` (4 hours). No functional impact
but misleading when reading job logs or assuming pruning frequency.

---

## LOW Findings

### L-1: compression.threshold=0.35 (below documented default of 0.50)
**File:** `config.yaml`; documented default per skill: 0.50  
Config compresses earlier than default. Combined with `micro_compact=True` and
`micro_compact_every_n_turns=3`, compression is aggressive. Not wrong, just a documented deviation.

### L-2: memory-facts/staging.md is empty (0 bytes)
**File:** `/var/home/rainbow/.hermes/memory-facts/staging.md`  
Either l1-extract ran successfully and flushed all facts, or produced nothing on the last run.
With the pipeline race condition (C-1), monitoring this regularly is warranted.

### L-3: stealth-browser-mcp.sh passes --minimal flag not in config args
**File:** `scripts/stealth-browser-mcp.sh` vs `config.yaml`  
Shell script uses `--minimal`; config doesn't include it. Mode mismatch between
config-driven and script-driven invocations (if/when server behavior differs with/without --minimal).

### L-4: no_agent=True jobs with enabled_toolsets=None — confirmed OK
Script-only jobs need no toolsets. This is the correct pattern. Not a defect.

### L-5: hourly-hermes-chat-sync naming: runs every 240m
Pure naming mismatch. No functional impact.

---

## Config.yaml Key Inventory (verified live)

| Key | Value | Notes |
|-----|-------|-------|
| `_config_version` | 34 | — |
| `memory.provider` | hindsight | Hindsight healthy (port 9177) ✓ |
| `agent.api_max_retries` | 1 | Below default of 3 — HIGH risk |
| `moa.presets.default.enabled` | false | Safe — but OpenAI ref latent |
| `compression.threshold` | 0.35 | Below documented 0.50 default |
| `compression.threshold_tokens` | 80000 | — |
| `compression.protect_last_n` | 15 | — |
| `compression.min_tail_user_messages` | 3 | — |
| `compression.proactive_prune_tokens` | 48000 | — |
| `compression.micro_compact` | true | — |
| `compression.micro_compact_every_n_turns` | 3 | — |
| `compression.idle_compact_after_seconds` | 1800 | — |
| `plugins.enabled` | [orca-status] | Only one plugin active |
| `mcp_servers.stealth-browser-mcp.enabled` | true | args BROKEN (C-2) |
| `mcp_servers.mempalace.enabled` | false | — |
| `mcp_servers.qmd.enabled` | false (implicit) | — |
| `mcp_servers.scrapfly.enabled` | false | — |

---

## Cron Job Inventory (all 13 jobs, last run status)

| Job Name | Schedule | no_agent | last_status | Notes |
|----------|----------|----------|-------------|-------|
| session-auto-prune | every 240m | true | ok | Name says "hourly"; runs every 4h |
| l1-extract-periodic | every 180m | true | ok | Header says 30m/no_agent=False |
| l1-promote-periodic | every 180m | true | ok | Races l1-extract (C-1) |
| l1-hindsight-promote | ~4h offset | true | ok | — |
| hermes-memory-drift-audit | daily | true | ok | Output dead-drop (H-2) |
| hermes-mutation-gate-watch | — | true | ok | Watches self-evolution dir |
| skillspector-guard | — | true | ok | — |
| firecrawl-watchdog | — | true | ok | No enabled_toolsets |
| hermes-platform-watchdog | — | true | ok | — |
| browser-orphan-watchdog | — | true | ok | No enabled_toolsets |
| omni-skill-quality-scan | — | true | ok | No enabled_toolsets |
| skill-prune-audit | 0 9 1 * * | true | **None** | NEVER RAN (H-4) |
| obsidian-weekly-review | — | false | ok | Dual script+prompt (M-3) |

---

## Pipeline Ordering Analysis

l1-extract and l1-promote have the same 180m interval. Ordering "guarantee":
- Creation-time offset: 3.942885 seconds (extract created first)
- next_run_at offset: same 3.942885 seconds
- This is NOT a structural guarantee — it's a coincidence of creation timing

Any of these break ordering:
- Scheduler restart (resets next_run_at calculation)
- l1-extract run takes > 4 seconds (promote fires while extract still running)
- Manual job execution resets timing

---

## Script Wiring Summary

| Script | Cron? | Config? | Status |
|--------|-------|---------|--------|
| groq-split-tunnel.sh | no | no | Orphan (Groq not configured) |
| mempalace-mcp.sh | no | yes (disabled) | Orphan |
| qmd-local.sh | no | yes (disabled) | Orphan |
| stealth-browser-mcp.sh | no | yes (enabled) | Args mismatch with config |
| canvas-offload.py | no | no | Utility, manual only |
| focus_compress.py | no | no | Utility, manual only |
| hermes-hud.py | no | no | Utility, manual only |
| memory-staleness.py | no | no | Utility, manual only |
| skill-graph-walk.py | no | no | Utility, manual only |
| issue-to-agents.py | no | no | Utility, manual only |
| adversarial_quarantine_review.py | no | no | Utility, manual only |
| hermes-memory-drift-audit.py | yes (daily) | no | Output silently discarded |
| l1-extract.py | yes (180m) | no | Header/config mismatch |
| l1-promote.py | yes (180m) | no | Races l1-extract |
| skill_prune_audit.py | yes (monthly) | no | Never ran |
| hermes-mutation-gate-watch.sh | yes | no | Working |
| session-prune.sh | yes (240m) | no | Name misleading (not hourly) |
