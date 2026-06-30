---
name: hermes-agent-sync
description: "Eliminate the dispatch→wait→synthesise→implement rework cycle: agents write typed JSON finding files; a deterministic applier applies them idempotently. Use when delegating parallel agents whose results need to be merged into real changes."
version: 2.0.0
author: Hermes
tags: [multi-agent, delegation, coordination, blackboard, idempotency, findings]
related_skills: [hermes-role-pipelines, subagent-driven-development]
---

# Hermes Agent Sync — Structured Findings Pattern

## Problem

Parallel delegated agents return prose summaries. Parent must:
1. Read all summaries
2. Manually synthesise what's new vs already done
3. Implement changes

This is slow, error-prone, and creates rework when agents overlap.

## Solution: Blackboard Findings Contract

Agents write typed JSON action payloads to a shared workspace.
Parent runs `apply-findings.py` once — no synthesis, no rework.

Workspace: `~/.hermes/agent-workspace/`
Schema: `hermes-finding/v1`
Applier: `python3 ~/.hermes/agent-workspace/apply-findings.py`

## When to use

- Dispatching 2+ parallel agents whose results touch shared files
- Any fan-out/fan-in pattern (see hermes-role-pipelines)
- When you want agents to produce machine-applicable changes, not prose

## How to use

### 1. Add this block to the `context` field of every delegated task

```
STRUCTURED OUTPUT CONTRACT (hermes-finding/v2):
Do NOT return a prose summary as your final answer.
Write a findings file to:
  /var/home/rainbow/.hermes/agent-workspace/<agent_id>-<task_label>.finding.json

Required envelope:
  {"schema": "hermes-finding/v2", "agent_id": "...", "task_label": "...",
   "generated_at": "<ISO8601>", "findings": [...]}

Each actionable change must be a typed finding:
  patch | file_append | file_write | config_set | git_commit | observation

Every finding MUST include:
  - idempotency_key: stable globally-unique string (format: <component>-<desc>-v<N>)
  - rationale: one-line reason
  - status: "ready" (or "proposed" if uncertain — will be deferred automatically)
  - confidence: 0.0–1.0 (below 0.5 deferred; omit = 1.0)
  - evidence: list of supporting sources/refs (URLs, file:line, quotes)

Use depends_on to order sequential changes (e.g. patch before git_commit).
Use supersedes to replace an earlier idempotency_key with a corrected version.
Non-actionable findings use type=observation.
After writing the file, return ONE line: "Findings written to <filename>, N findings."
```

### 2. After dispatching agents — fully automatic

The `subagent_stop` hook auto-runs apply-findings.py the moment each agent
completes and returns the apply summary as context to the parent LLM.
No manual step needed. No `--watch` needed.

Manual apply (if needed for debugging or re-runs):
```
python3 ~/.hermes/agent-workspace/apply-findings.py --dry-run   # preview
python3 ~/.hermes/agent-workspace/apply-findings.py             # apply
```

Applied keys stored in `.applied-keys`. Re-running is always safe.
Processed files renamed from `.finding.json` to `.finding.done`.

### 3. Complexity-gated injection (automatic)

The `pre_llm_call` hook classifies every query on four axes (0-3 each):
  parallelism potential, research depth, implementation breadth, ambiguity

  score 0-3  → no injection (simple queries left alone)
  score 4-6  → delegation routing hints
  score 7-9  → routing hints + full findings contract injected into context
  score 10+  → all of above + parallel fan-out instruction

No configuration needed — it fires automatically on every turn.

## Finding types

| type | use for | idempotent via |
|------|---------|---------------|
| patch | edit file region | new_string presence check |
| file_append | append to file | sentinel string check |
| file_write | create/overwrite file | key registry |
| config_set | hermes config set key value | key registry |
| git_commit | stage + commit in repo | key registry |
| observation | audit results, gap notes | always applied (just logged) |
| shell | arbitrary command | BLOCKED by default; requires _allowlisted:true |

## v2 triage fields

| field | effect |
|-------|--------|
| status=proposed | deferred (agent still drafting) |
| confidence < 0.5 | deferred automatically |
| depends_on: [key] | applied after dependency |
| supersedes: [key] | old key skipped in same file |
| evidence: [...] | logged alongside result for traceability |

## Idempotency key convention

  `<component>-<change-description>-v<N>`

Examples:
  threat-patterns-img-exfil-v1
  config-delegation-effort-medium
  memory-model-routing-v2

## Pitfalls

- Agents must write the file BEFORE returning — instruct them explicitly
- `patch` requires exact old_string match; include enough context lines
- `git_commit` should come last within a finding file (after patches)
- Don't use `shell` type for automated agents — prefer typed action types
- If an agent returns prose instead of a finding file, fall back to manual apply; add a reminder to context next time
- The applier archives to `.finding.done` only on zero errors — fix errors before re-running
