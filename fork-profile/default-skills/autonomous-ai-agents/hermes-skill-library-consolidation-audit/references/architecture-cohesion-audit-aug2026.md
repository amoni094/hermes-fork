# Architecture Cohesion Audit — Aug 2026

Surface to run when the user asks "does the architecture work cohesively" or "make sure
everything is wired up". Distinct from skill library quality — this is about runtime
integration: scripts, cron jobs, and skills all referring to each other correctly.

## Step 1 — Build the cross-reference map

Write and run an ad-hoc Python script (write_file + terminal) that:
1. Lists every script in ~/.hermes/scripts/
2. For each script, text-searches all other scripts, all SKILL.md files, and the hermes
   cron list output for references by filename (check both `script.py` AND bare `script`)
3. Reports: callers (who references this script), cron coverage, skill mention coverage
4. Classifies orphans: scripts with zero callers AND no cron AND no skill mention

Do NOT use a simple regex stem-match — it misses subprocess calls using full path strings
(`str(Path(__file__).parent / 'script.py')`) or cron `Script:` fields. Text-search both
the stem and the full filename across scripts, SKILL.md files, and cron list stdout.

Clean up any temp scripts with rm afterward.

## Step 2 — Classify orphans

Expected legitimate orphans — do NOT treat these as gaps:
- MCP launcher scripts (`stealth-browser-mcp.sh`, `mempalace-mcp.sh`) — started by Hermes config
- Login/manual scripts (`groq-split-tunnel.sh`) — by design, not cron-driven  
- Manual git utilities (`skills-commit.sh`) — invoked by user, no automation
- On-demand tools (`l1-context-offload.py`, `memory-provenance.py`) — no cron needed

Real orphans (action required):
- New script created to implement a research finding, not yet referenced anywhere
- Script that lost its cron job (deleted, never recreated)
- Script implementing a feature documented in a skill but not mentioned in the skill body

## Step 3 — Check pipeline data flow continuity

For each pipeline, trace: trigger → script → output → consumer.

| Pipeline | Trigger | Scripts | Output | Consumer |
|----------|---------|---------|--------|----------|
| L1 memory | cron every 180m | l1-extract.py → l1-promote.py | staging.md → Hindsight | l1-gmemory-consolidation.py (nightly) |
| Skillspector | cron every 240m | skillspector_guard_enforce.sh → skillspector_guard.py | last-summary.json | human review |
| Adversarial review | auto-called by --enforce | adversarial_quarantine_review.py | reports/adversarial/*.json | human (confirm/reject) |
| Omni-scan | cron weekly Sunday | omni_skill_scan.py | patch-queue.json | human + gepa (optional) |
| Skill router | called by omni-scan | skill-router-index.py | ~/.hermes/cache/skill-router-index.pkl | --query at task time |
| Pending improvements | trace2skill.py on demand | (staged by agent after complex task) | pending-improvements/*.md | pending-improvements-review cron (Sunday) |
| Memory sentry | daily via drift-audit | hermes-memory-drift-audit.py → am-sentry.py | am-sentry-report-*.json | human review (if HIGH flags) |

Look for dangling producers (output nobody reads) and new scripts added to skill docs
but not wired into any cron or caller.

## Step 4 — Verify integration hooks actually fire

For subprocess wiring inside scripts, verify:
- Path is correct: `Path(__file__).parent / 'script.py'` not hardcoded absolute paths
- Timeout is set: slow scripts called from fast cron need a subprocess timeout
  (am-sentry.py called from drift-audit: use 15s max, not 30s — Hindsight queries are slow)
- Return code is checked: 0 = clean, 1 = flags found, other = error
- Output reaches cron consumer: print to stdout so it appears in cron output

## Integration wiring added Aug 2026

| Script | Wired into | How |
|--------|-----------|-----|
| skill-router-index.py | omni_skill_scan.py | subprocess call after scan, --build then --check |
| trace2skill.py | self-improve-agent skill + pending-improvements-review cron | skill doc trigger + Sunday 10am cron |
| am-sentry.py | hermes-memory-drift-audit.py | subprocess call at end of drift audit, --since 1 |
| adversarial_quarantine_review.py | skillspector_guard.py --enforce | auto-called when newly_proposed is non-empty |
| skill-yield-tracker.py | omni_skill_scan.py | subprocess --audit call before SUMMARY block (Aug 2026) |
| news_diff_watchdog.py | cron job news-diff-watchdog | every 90m, no_agent=True; feeds: Reuters, HN, MIT Tech, Guardian AU (Aug 2026) |

## Pitfall: execute_code triple-quoted terminal() SyntaxError

Do NOT nest triple-quoted heredocs inside execute_code terminal() calls:

```python
# FAILS — outer """ and heredoc closing """ collide
r = terminal("""python3 << 'EOF'
...
EOF
""")
```

Use write_file + terminal instead:
```python
write_file('/tmp/script.py', '...')
terminal('python3 /tmp/script.py && rm /tmp/script.py')
```

## Pitfall: cron list doesn't expose scripts via state.db

state.db has no `config` column (confirmed Aug 2026). Do not try to read cron job
configuration from the database. Use `hermes cron list` stdout and parse it:

```bash
hermes cron list 2>/dev/null | grep -E 'Name:|Script:|Skills:'
```

## Pitfall: delegate_task rejects goal text with angle brackets

delegate_task's template-marker check rejects goal text containing `<word>` patterns
even when they're not templates (e.g. `<10s`, `<session_id>`, `<list>`). This causes
a hard rejection with "unexpanded template marker" error. Fix: replace angle brackets
with square brackets or plain text in all goal/context strings.

## Audit outcome (Aug 2026)

- 48 total scripts: 42 covered (cron/script/skill reference), 6 legitimate orphans
- All 14 cron script references point to existing files on disk
- All scripts referenced in skill SKILL.md bodies exist on disk
- 2 real gaps found and fixed (original audit):
  1. adversarial_quarantine_review.py never called automatically → wired into --enforce
  2. pending-improvements drain had no cron → pending-improvements-review cron added (Sunday 10am)
- 2 additional gaps found and fixed (Aug 2026 follow-up):
  3. skill-yield-tracker.py (SYNAPSE) existed but had no callers → wired into omni_skill_scan.py --audit
  4. news_diff_watchdog.py had feeds commented out and no cron → feeds populated + news-diff-watchdog cron added (every 90m, no_agent)
- l1-hindsight-promote WARN false positive: "Zero failures" in output triggered keyword
  match but is a clean result (the word "failures" appeared in a success summary)
