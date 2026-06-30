# Multi-Agent Orchestrator Budget Patterns

Reference architectures and tuning strategies from production multi-agent systems:
Veto (PlawIO), Helmor, Orca, Superset, Sandcastle, Vibe Kanban, Lanes.

## Budget Scope

**Veto (PlawIO/veto)**: Policy-driven governance with declarative execution constraints.
- Tracks: function calls, compute time, token spend, memory footprint
- Enforcement: pre-execution hook checks policy, halts violating calls
- Interface: Python SDK with typed policy objects
- Tuning: edit policy dict at runtime, no restart

**Hermes implementation**: Simplified to three metrics (tool_calls, destructive_calls, delegation_depth).
- Why three: these are observable without LLM inference cost
- tool_calls: cheap proxy for session runaway (agent loops, retry storms)
- destructive_calls: safety boundary for irreversible ops
- delegation_depth: prevents deep subagent cascades (Hermes-specific)

## Warning vs. Hard Block

Most systems distinguish soft warnings from hard blocks:

| System | Soft Warn | Hard Block |
|--------|-----------|-----------|
| Veto | 75% | 100% (then policy decision) |
| Helmor | 80% | 90% (reserves margin) |
| Orca | 70% | 95% (early margin) |
| Hermes | 85% | 100% (no margin) |

**When to add margin** (reserve unburnable budget):
- Long-running sessions where partial results are valuable (research, analysis)
- Batch operations with expected variance (crawl, test sweep)
- Delegation-heavy work where subagents may overestimate

**No margin** is right for:
- Interactive CLI sessions (fast fail is better than partial lockout)
- Agentic loops (clear signal to break and evaluate)

## Destructive Ops Classification

Different systems define "destructive" differently:

**Strict (Sandcastle)**: Only actual delete/drop commands.
```
Flags: rm, rmdir, DROP TABLE, DELETE FROM
```

**Medium (Helmor, Orca)**: Delete + file overwrites.
```
Flags: rm, rmdir, shred, write_file, patch (with content change), DROP, DELETE, truncate
```

**Permissive (Veto)**: Any op that mutates persistent state.
```
Flags: above + git commit, API POST/PUT, network writes, database updates
```

**Hermes current**: Medium (terminal rm/shred, write_file, patch).
- Rationale: balance between safety and usability
- Terminal writes via `echo >> file` are not caught (use write_file instead)
- Git commits are not flagged (they're usually correct)
- API calls not flagged (would require request inspection)

**If you need stricter**: Extend track-budget.py to flag more patterns.
**If you need looser**: Remove items from the destructive_patterns set.

## Delegation Depth Control

**Why limit depth**: Subagent cascades can hide control flow and cost assessment.
- Agent A delegates to B, which delegates to C, which creates D...
- Token spend, wall-clock time, and error recovery are opaque to A
- Cost surprises emerge late (at depth 4+)

**Helmor pattern**: limit to 3, with explicit depth param in delegated prompts.
- Depth 0 = main agent
- Depth 1 = direct subagents
- Depth 2 = subagents of subagents (rare, usually a smell)
- Depth 3+ = design flaw, should be collapsed

**Hermes default**: 4 (one level more permissive for now).
- Adjust down to 3 if you see cascades in your work
- Adjustment: `hard_limits: delegation_depth: 3` in budget-policy.yaml

## Session Lifetime Budgets

Most systems support per-session budgets (like Hermes) and per-run budgets (Ouroboros Seed):

**Per-session**: covers a whole interactive session or a cron job tick
- Tool calls: 500–1000 (interactive) or 100–300 (cron, bounded)
- Destructive ops: 20–50 (interactive) or 5–10 (cron, safety first)
- Delegation depth: 3–4

**Per-run (Seed)**: a single task execution within a session
- Much tighter (100–200 tool calls)
- Dangerous ops (0–5)
- Single-level delegation only

**Hermes**: currently per-session only. To add per-Seed budget tracking:
1. Update agent-hooks to track Seed ID (if available in hook payload)
2. Write per-seed state files: `budget-<session_id>-<seed_id>.json`
3. Add seed_depth counter (separate from delegation_depth)

## Tuning Profiles

### Interactive Development (default)
```yaml
hard_limits:
  tool_calls: 500
  destructive_calls: 30
  delegation_depth: 4
soft_warn_pct: 0.85
```

### Research / Analysis (high tool calls, low destructive)
```yaml
hard_limits:
  tool_calls: 2000
  destructive_calls: 5
  delegation_depth: 2
soft_warn_pct: 0.80
```

### Batch / Automation (low tool calls, high destructive, 1 delegation level)
```yaml
hard_limits:
  tool_calls: 300
  destructive_calls: 100
  delegation_depth: 1
soft_warn_pct: 0.75
```

### Data Pipeline (high everything)
```yaml
hard_limits:
  tool_calls: 5000
  destructive_calls: 200
  delegation_depth: 3
soft_warn_pct: 0.70
```

## Troubleshooting

**Budget warning but tasks are legitimate?**
→ You're hitting the limit for that workload class. Update the profile above to match your session type, or raise the limit for one session:
```yaml
hard_limits:
  tool_calls: 1000  # increased
```

**Destructive limit hit, but no risky ops observed?**
→ Check the hook's destructive_patterns set. It may be flagging grep/read/inspection ops.
→ Verify: `grep -n "destructive_patterns\|FLAGS:" ~/.hermes/agent-hooks/track-budget.py`

**Delegation depth stuck at 0?**
→ The hook payload is missing delegation_depth field. Verify hook wiring:
`hermes config get hooks.tracking`

**State files piling up in ~/.hermes/state/?**
→ Old session state. Safe to delete:
`find ~/.hermes/state -name 'budget-*.json' -mtime +7 -delete`

## References

- Veto (PlawIO): https://github.com/PlawIO/veto
- Helmor: https://github.com/helmor-dev/helmor
- Orca: Multi-agent orchestrator (patterns observed in public demos)
- Awesome Multi-Agent Orchestrators: https://github.com/Agent-Analytics/awesome-multi-agent-orchestrators
