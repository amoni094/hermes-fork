---
author: Hermes
depends_on: [dispatching-parallel-agents, subagent-output-contract]
provides: [idempotent-findings, blackboard-apply, typed-json-findings]
description: 'Use when: delegating parallel agents whose results need idempotent application. Eliminate the dispatch→wait→synthesise→implement
  rework cycle: agents write typed JSON finding files; a deterministic applier applies them.'
name: hermes-agent-sync
related_skills:
- hermes-role-pipelines
- subagent-driven-development
- subagent-output-contract
- hermes-context-packet
- hermes-swarm-consensus
tags:
- multi-agent
- delegation
- coordination
- blackboard
- idempotency
- findings
triggers:
- dispatching 2+ parallel agents whose results touch shared files and must be merged
- fan-out/fan-in pattern where agents should write machine-applicable JSON findings rather than prose summaries
- wanting structured JSON output from subagents so a deterministic applier can merge changes idempotently
- avoiding the dispatch→wait→synthesise→implement rework cycle on multi-agent tasks
version: 2.0.0
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

**Merging conflicting findings:** When multiple agents propose changes to the same file,
`apply-findings.py` applies them in dependency order (via `depends_on` graph).
For verdict-type findings (e.g., architecture decisions, consensus votes), use the
`hermes-swarm-consensus` skill to reduce multiple agent opinions into a deterministic
majority/arbiter verdict before writing the merge finding.

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

## Sub-Agent Intent Queue Pattern (Equational Applications, Aug 2026)

## Context RSS (CRSS) — Context as Append-Only Event Feed (HN, Aug 2026)

cRSS (gitlab.com/0xc4ff31n3/crss) turns LLM context mutation into a structured, deterministic, auditable event feed (RSS + event sourcing + git-like diffs). Key patterns applicable to Hermes multi-agent sync:

**Context-as-event-log**: every context change is an immutable event (not an in-place mutation). Agents subscribe to each other's event feeds rather than sharing a mutable state blob. Agent B can know what Agent A told the user because it replays Agent A's event log — no shared mutable memory needed.

**Deterministic replay**: any agent can reconstruct exactly what went into another agent's inference by replaying its event feed up to a given point. This makes cross-agent debugging tractable: "why did Agent B make that decision?" → replay Agent B's context events up to that turn.

**Multi-agent context sharing without coupling**: agents share feeds, not sessions. Agent A's context is Agent A's — Agent B only consumes the exported feed. No shared mutable workspace, no race conditions on context state.

**Hermes approximation**:
- The blackboard contract (existing pattern) handles finding/result sharing. CRSS complements it with full context-event provenance.
- When debugging a cross-agent failure: use `session_search(session_id, around_message_id)` to reconstruct the event sequence in each agent's session — this is the manual CRSS equivalent already in Hermes.
- For high-stakes multi-agent tasks: emit a Hindsight entry per major context event (task received, tool called, finding produced, decision made) with `tags: ["agent-event", agent_id]`. This creates a queryable event log for post-hoc attribution.

Reference: gitlab.com/0xc4ff31n3/crss, HN Show HN Aug 2026.

Parallel sub-agents that write directly to shared state (memory, files, Hindsight) risk contention when multiple agents write simultaneously. The intent-queue pattern:

1. Sub-agents emit **intents** (structured delta messages) instead of direct writes:
   ```json
   {"op": "upsert_memory", "key": "ppor_research", "value": "...", "agent_id": "subagent-3"}
   ```
2. All intents go to a single SQLite queue table:
   ```sql
   CREATE TABLE intents (id INTEGER PRIMARY KEY, ts TEXT, agent TEXT, op TEXT, payload JSON);
   ```
3. A single **coordinator** (the parent agent) drains the queue and applies intents atomically after sub-agents complete.

This eliminates write contention and produces an auditable record of every sub-agent output. Source: sqlite-s3-agent-tutorial (Equational Applications, Aug 2026).

In Hermes: use this pattern whenever `delegate_task(tasks=[...])` produces results that all write to the same memory surface. Instead of each task calling `memory(action='add', ...)` directly, have tasks return structured intent JSON in their output, and have the parent apply them sequentially.

## Versioned Inter-Agent Result Schema (arXiv:2608.11897) ★ MED — Sweep 12

**Per delegated task type:** keep a versioned result schema for each delegated task type (not one global envelope only). `hermes-finding/v2` is the shared envelope; each `task_label` / task class should pin its own `findings[]` item schema version so a research-finder payload cannot be parsed as a patch payload. Validate that schema on RECEIPT in the parent before `apply-findings.py` (GUIDE, arXiv:2608.12133: 96% task success with receipt validation). <!-- why: prevents silent cross-type deserialize of parallel agent findings -->

Source: "Schema Versioning for Multi-Agent Result Exchange". Key finding: multi-agent pipelines
fail silently when one agent is updated and its result schema changes without bumping a version
field — downstream consumers parse stale field names and produce wrong output with no error.

**Fix: add a `schema_version` field to every inter-agent result:**
```json
{
  "schema_version": "1.2",
  "agent_id": "subagent-research-3",
  "findings": [...],
  "status": "complete"
}
```

**Version bump rules:**
- Patch (1.0 → 1.0): add optional fields. No consumer update required.
- Minor (1.0 → 1.1): rename a field or change its type. Consumers must handle both.
- Major (1.0 → 2.0): remove a field or change schema structure. Requires coordinated update.

**Hermes implementation:**
For any `delegate_task` pipeline that runs repeatedly (cron, nightly sweeps, iterative agents):
1. Add `"schema_version": "1.0"` to the `output_schema` as a required const field.
2. When updating what a subagent returns, bump the version and update the parent's validation.
3. In the parent: check `result["schema_version"]` before deserialising — raise if unexpected.

```python
EXPECTED_SCHEMA_VERSION = "1.0"
for r in results:
    if r.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise ValueError(f"Schema mismatch: got {r.get('schema_version')}, expected {EXPECTED_SCHEMA_VERSION}")
```

**Pitfall:** The most common failure is skipping the version field on first implementation
("we'll add it later") — by the time schema drift occurs, the history is unrecoverable.
Add it from the first iteration, even if version stays at "1.0" forever.

## Role Declaration Protocol (arXiv:2609.03111)

Each `delegate_task` goal MUST declare:
- `role=` one of: `researcher` | `implementer` | `reviewer` | `synthesizer` | `extractor`
- `boundary_actions=` list of tool types this role is allowed to call

Mailbox handoff must include the **sender's declared role**.

If a received handoff is from a role that does **not** match the expected sender, log a **trust-weight reduction** and treat that finding as **MED not HIGH**.

Cross-link: `dispatching-parallel-agents` § Role Drift Detection in Hierarchical MAS (arXiv:2609.03111).

## RACS prefix-drift tracker

RACS prefix-drift tracker: run `/var/home/rainbow/.hermes/scripts/racs-prefix-tracker.py` periodically to detect response-prefix drift across sessions. Invoke after every 10 sessions or weekly via cron.

No `racs` or `prefix_drift` keys exist in `~/.hermes/config.yaml` (`hermes config set context.log_prefix_drift` is not a supported key). The script is the implementation; there is no cron job for it in `~/.hermes/cron/jobs.json`.

Weekly cron recommendation (script is fully functional, not a stub):
```
# weekly RACS prefix-drift report
0 9 * * 1 python3 /var/home/rainbow/.hermes/scripts/racs-prefix-tracker.py --report
```
Report logs: `~/.hermes/logs/prefix-drift.jsonl`. Import path: `track_turn(session_id, turn_num, blocks)`.

## Pitfalls

- Agents must write the file BEFORE returning — instruct them explicitly
- `patch` requires exact old_string match; include enough context lines
- `git_commit` should come last within a finding file (after patches)
- Don't use `shell` type for automated agents — prefer typed action types
- If an agent returns prose instead of a finding file, fall back to manual apply; add a reminder to context next time
- The applier archives to `.finding.done` only on zero errors — fix errors before re-running
