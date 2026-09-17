# Recursive Adversarial Self-Audit Pattern

Distilled from multi-pass Hermes self-improvement runs (Passes 1–5, 2026-07-03).

## Pattern overview

A recursive adversarial audit is a loop of:
  Phase 1: Gather → Phase 2: Analyze → Phase 3: Fix → Phase 4: Verify → Phase 5: Recurse

It terminates when no C/H/M severity issues remain unfixed. Low items may carry over if
they require user input (e.g. unfixable upstream CVEs).

## What to audit per run

Each pass should cover ALL five domains. Missing one means it accumulates silently:

1. Memory architecture — redundancy, stale entries, surface overlap, correctness
2. Workflow efficiency — dead crons, duplicate jobs, scripts with stale assumptions
3. Token optimization — model routing, compression config, skill catalog bloat, unused assets
4. Security — API key handling (.env hygiene), script permissions, CVEs, trust boundaries
5. Efficiency — disk usage, never-used skills (use_count=0 AND view_count=0), cold-start cost

## Context carry between passes

CRITICAL: each pass must carry forward an explicit "WHAT PRIOR PASSES FIXED" list.
Without it, the next pass will re-diagnose and potentially re-fix already-resolved items.

Format for the carry-forward list (put in context= of delegate_task, not goal=):
```
WHAT PRIOR PASSES ALREADY FIXED (do not re-fix):
- CRITICAL: <description> (date fixed, verification method)
- HIGH: <description>
- MEDIUM: <description>
- LOW: <description> — confirmed intentional / confirmed clean
```

Include false positives explicitly with the label "confirmed false positive" so they
are not re-raised on the next pass.

## Severity classification

- CRITICAL: breaks agent operation, silent data loss, security exposure
- HIGH: operational risk, major waste, cron collision, dead code that misleads
- MEDIUM: efficiency loss, redundancy, stale config that will mislead future agents
- LOW: minor hygiene, unused assets, documentation gaps

Recurse until CRITICAL + HIGH + MEDIUM are all resolved. LOW items can be closed
with a "confirmed intentional" or "confirmed clean" label if they are by-design.

## Useful baseline check commands

```bash
# Hermes doctor (full health check)
hermes doctor

# All crons and their last-run status
hermes cron list

# Watchdog smoke test
bash ~/.hermes/scripts/hermes-platform-watchdog.sh; echo "EXIT: $?"

# Never-used skills (use_count=0 AND view_count=0)
python3 -c "
import json
u = json.load(open('/var/home/rainbow/.hermes/skills/.usage.json'))
never = [(k,v) for k,v in u.items() if v.get('use_count',0)==0 and v.get('view_count',0)==0]
for k,v in sorted(never): print(k, v.get('last_patched_at',''))
"

# Config verification (no 'hermes config get' — it doesn't exist)
python3 -c "import yaml; d=yaml.safe_load(open('/var/home/rainbow/.hermes/config.yaml')); print(d.get('delegation',{}))"

# Script disk usage
du -sh ~/.hermes/skills/*/  | sort -rh | head -20
```

## Fable-5 as orchestrator for adversarial audits

Fable-5 is the best model for this pattern due to:
- Extended thinking for adversarial security reasoning
- Dependency DAG generation before execution
- Self-verification before applying changes

Pattern B invocation (from a running session):
1. `hermes config set delegation.model claude-fable-5`
2. `hermes config set delegation.provider anthropic`
3. `hermes config set delegation.max_spawn_depth 2`
4. `hermes config set delegation.max_concurrent_children 4`
5. Verify written: `python3 -c "import yaml; print(yaml.safe_load(open('~/.hermes/config.yaml'))['delegation'])"`
6. dispatch delegate_task (background — it returns immediately)
7. IMMEDIATELY restore: `hermes config set delegation.model mistral-small-latest && hermes config set delegation.provider mistral && hermes config set delegation.max_spawn_depth 1`
   Then restore `max_concurrent_children` to whatever it was BEFORE step 1.
   (`mistral-small-latest` is the verified live leaf default as of 2026-08-25. Do not restore to `claude-sonnet-4-6`.
   max_concurrent_children is user-configured — check before overriding with a hardcoded value.) <!-- why: hardcoding restore to 3 was wrong; user's live config has 10 -->

## Common findings across passes

These have appeared repeatedly and should be checked on every pass:

- Duplicate cron jobs (e.g. two session-prune jobs at different schedules)
- Empty/duplicate env var entries in .env (especially blank ANTHROPIC_API_KEY lines)
- Skills with use_count=0, view_count=0, and large disk footprint — safe to delete
- Platform-watchdog scripts with hardcoded config key names that have been renamed
- WhatsApp bridge npm CVE (Baileys protocolMessage spoofing) — unfixable upstream, bridge dormant; do not re-flag

## False positives to ignore

- compression_model: claude-3-5-haiku-20241022 — valid alias, not a stale model name
- firecrawl_watchdog.sh silent exit-0 on healthy — correct no-agent pattern, not a visibility bug
- orca-status plugin __init__.py minimal content — correct; it's a local hook relay
