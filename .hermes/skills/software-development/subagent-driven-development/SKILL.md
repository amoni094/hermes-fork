---
name: subagent-driven-development
description: "Implement larger tasks with focused Hermes subagents, compact context packets, and explicit review/verification handoffs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, multi-agent, implementation, verification, review]
    related_skills: [workflow-map, hermes-role-pipelines, hermes-acp-routing, complexity-gated-planning, requesting-code-review, verification-before-completion]
---

# Subagent-Driven Development

Use this skill when a task is big enough, noisy enough, or separable enough that a fresh worker context will improve quality.

## Core Principle

Use subagents to reduce context overload and separate roles, not to add ceremony for its own sake.

## When to Use

Use this when one or more are true:
- the task naturally splits into discovery, implementation, and review
- the codebase area is large enough that one agent would drown in search output
- independent subtasks can run in parallel
- you want a fresh reviewer that did not author the change
- the user explicitly asks for parallel agents or subagents

Avoid this when:
- the task is tiny and obvious
- the work depends on constant back-and-forth with the user
- the task is mostly a single shell command or one file edit
- there is no clean boundary between subtasks

Start by loading `workflow-map` and `complexity-gated-planning` to decide whether delegation is justified.

## Standard Role Split

Use the smallest split that fits the task.
Choose the collaboration pattern first, then the worker labels.

### Pattern A — Discovery -> Implement -> Verify
Harness mapping: Pipeline.
1. discovery worker
2. implementation worker
3. verification/review worker

### Pattern B — Parallel discovery -> single implementation -> review
Harness mapping: Fan-out / Fan-in -> Producer-Reviewer.
1. parallel discovery workers for independent surfaces
2. one implementation worker using their findings
3. one reviewer/final verifier

### Pattern C — Planner -> implementer -> reviewer
Harness mapping: Producer-Reviewer.
Use this when the shape of the change is unclear at the start.

### Pattern D — Parent supervisor with worker waves
Harness mapping: Supervisor.
Use this when new findings may change what should be edited next. The parent keeps the todo list and dispatches narrowly scoped waves instead of trying to pre-plan every child.

### Pattern E — Conditional specialist dispatch
Harness mapping: Expert pool.
Use this when only some specialties are needed depending on what discovery finds; for example, spawn security only if secrets/auth are touched.

### Not supported directly — Hierarchical delegation
Harness includes hierarchical delegation, but Hermes children here cannot spawn further children. Flatten the tree into parent-managed waves.

## Compact Context Packet

Every worker prompt should include only:
- exact goal
- exact file paths or directories
- exact errors, failing commands, or acceptance criteria
- scope limits
- required output contract

Good output contract:
- changed files
- commands run
- pass/fail result
- unresolved risks

Do not dump the whole conversation. Do not pass irrelevant files.

## Hermes Delegation Pattern

Use `delegate_task` directly.

Single worker:
```python
delegate_task(
  goal="Implement the fix for the failing cache invalidation path.",
  context="Files: src/cache.py, tests/test_cache.py. Acceptance: failing test passes, no unrelated edits. Return changed files and exact test commands run.",
  toolsets=["terminal", "file"]
)
```

Parallel workers:
```python
delegate_task(tasks=[
  {
    "goal": "Inspect the auth middleware path and identify likely failure points.",
    "context": "Read-only. Return affected files, likely root cause, and any missing tests.",
    "toolsets": ["terminal", "file"]
  },
  {
    "goal": "Inspect the session persistence path and identify likely failure points.",
    "context": "Read-only. Return affected files, likely root cause, and any missing tests.",
    "toolsets": ["terminal", "file"]
  }
])
```

## Required Handoffs

### Before implementation
- decide whether `isolated-workspace-preflight` is needed
- decide whether `test-driven-development` applies
- check local workspace or vault context first before spawning workers, so delegation starts from current project reality rather than a stale chat summary
- state the acceptance criteria in the worker context

## Delegation Boundary and Durability

Use ordinary subagents only for bounded work that can safely die with the current session.

- before delegation, inspect the local workspace/vault context and then pass a compact context packet, not a raw conversation dump
- if the work must outlive the current turn or session, prefer a durable mechanism such as background Hermes runs or cron instead of ordinary delegation
- long-lived work should leave an inspectable trail in `~/.hermes/logs/hermes-task-ledger.jsonl` so future sessions can recover state

### After implementation
- run `requesting-code-review` or at least the review depth chosen by `risk-based-review`
- use `verification-before-completion` before claiming success

## Recommended Review Model

The implementer should not be the final verifier for non-trivial work.

Preferred sequence:
1. implementation worker makes the change
2. reviewer worker checks diff, risks, and regressions
3. parent agent verifies any claimed side effects with direct tool calls

## Integration with Autonomous-Agent Skills

**hermes-role-pipelines:** Use when you want named specialist roles such as finder, debugger, coder, reviewer, tester, or security rather than generic worker labels.

**hermes-acp-routing:** Use when you want to route a narrow implementation task through a verified ACP-compatible external CLI. Prefer normal Hermes delegation unless ACP transport is known-good.

**workflow-map:** Use first to decide whether the task needs delegation at all.

## Anti-Patterns

Do not:
- spawn workers for trivial edits
- pass giant unfiltered context blobs
- trust a worker claim of success without verification
- let implementation and final verification collapse into the same fresh-context role on risky changes
- keep looping workers without tightening the scope after failures

## Minimum Safe Pattern

For any non-trivial delegated coding task:
1. compact context packet
2. implementation worker
3. independent review
4. direct verification by parent or final verifier

## Completion Rule

Do not say the task is done until the delegated results have been checked against fresh evidence with `verification-before-completion`.
