---
name: hermes-budget-governance
description: >
  Session budget enforcement for Hermes. Tracks tool call counts, destructive
  operations, and delegation depth per session. Warns at 85% and blocks at 100%
  of configured limits. Use when you need to understand or adjust the budget system,
  troubleshoot budget warnings, or tune the policy for a long-running session.
triggers:
  - budget exceeded
  - budget warning
  - tool call limit
  - session limit
  - governance enforcement
  - budget policy
---

# Hermes Budget Governance

Implements pre-execution governance inspired by Veto (PlawIO/veto) and the
Microsoft Agent Governance Toolkit. Deterministic limits enforced via agent hooks.

## Architecture

```
post_tool_call hook:  ~/.hermes/agent-hooks/track-budget.py
  -> reads policy:   ~/.hermes/budget-policy.yaml
  -> writes state:   ~/.hermes/state/budget-<session_id>.json
  -> context inject: warns parent LLM at 85%, exits non-zero at 100%

subagent_start hook:  ~/.hermes/agent-hooks/track-subagent-hud.py
  -> writes HUD:     ~/.hermes/state/hud-active-agents.json

subagent_stop hooks:  ~/.hermes/agent-hooks/log-subagent-stop.py (original)
                      ~/.hermes/agent-hooks/clear-subagent-hud.py (HUD cleanup)
```

## Policy file

~/.hermes/budget-policy.yaml:
```yaml
hard_limits:
  tool_calls: 500          # total invocations per session
  destructive_calls: 30    # rm/DROP/DELETE/write_file ops
  delegation_depth: 4      # max subagent nesting

soft_warn_pct: 0.85        # warn at 85%
```

Edit this file to tune limits. No restart required — hooks read it fresh each call.

## View current budget state

```bash
# Latest session's budget:
ls ~/.hermes/state/budget-*.json | sort -t- -k2 | tail -1 | xargs cat

# HUD (shows active agents + budgets):
python3 ~/.hermes/scripts/hermes-hud.py

# Watch mode (refreshes every 3s):
python3 ~/.hermes/scripts/hermes-hud.py --watch
```

## What counts as "destructive"

The hook flags a call as destructive when the tool name is in
{terminal, write_file, patch} AND the arguments contain any of:
  rm, rmdir, shred, DROP TABLE, DROP DATABASE, DELETE FROM, truncate

## Tuning for long sessions

If you hit the tool_calls limit on legitimate long tasks, increase it:
```yaml
hard_limits:
  tool_calls: 1000
```

Or raise destructive_calls for bulk file operations:
```yaml
hard_limits:
  destructive_calls: 100
```

## Pitfalls

- The hook uses session_id from the hook payload. If session_id is missing/unknown,
  state goes to `budget-unknown.json` — check that first if state seems stale.
- delegation_depth tracking depends on the hook payload including `delegation_depth`.
  If that field is absent, depth tracking stays at 0.
- Policy YAML requires PyYAML. If unavailable, policy falls back to hardcoded defaults.
  Install: `uv pip install pyyaml --user`
- The hook exits with code 2 on breach. Hermes must have `hooks_auto_accept: true` or
  the exit code won't block tool execution.

## Skills versioning

The skills directory is git-tracked at ~/.hermes/skills (root repo at ~/.hermes).
To snapshot skills after changes:
```bash
cd ~/.hermes/skills
git add -A
GIT_AUTHOR_EMAIL=hermes@local GIT_COMMITTER_EMAIL=hermes@local \
  GIT_AUTHOR_NAME=Hermes GIT_COMMITTER_NAME=Hermes \
  git commit -m "skills: describe change"
git log --oneline -5
```
