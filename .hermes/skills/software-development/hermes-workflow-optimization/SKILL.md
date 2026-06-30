---
name: hermes-workflow-optimization
description: "Use when you need the Hermes workflow optimization playbook for choosing the smallest capable model, keeping prompt packets stable, and keeping work explicit and bounded."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, workflow, optimization, token-efficiency, model-selection]
    related_skills: [hermes-agent, workflow-map, hermes-operating-pattern, hermes-context-budgeting, subagent-driven-development, verification-before-completion]
---

# Hermes Workflow Optimization

## Overview

Use this skill when you specifically want the token-efficiency and task-slicing playbook for Hermes work.

If you first need to choose the overall development workflow, load `workflow-map` instead. If you need the broader Hermes umbrella, load `hermes-operating-pattern`.

Use this skill to keep local agent work efficient without losing verifiability.

The core idea is simple: start from the runtime context, state the objective and boundaries up front, choose the smallest capable model, keep prompt prefixes stable, and keep each task small enough to verify independently.

## When to Use

- You are planning a local Hermes task and want to minimize token use.
- You need to choose between a small model, a stronger model, or a sub-agent.
- You want to keep prompts cache-friendly and reusable.
- You are deciding how to decompose a larger task into smaller bounded slices.

## Operating Rules

- Use the runtime-provided context first.
- State objective, scope, chosen model tier, and validation plan before editing.
- Prefer the smallest capable model that fits the task class.
- Keep immutable instructions first and task-specific details last.
- Keep each slice small enough to verify on its own.
- Prefer structured outputs over open-ended freeform when the result will be reused.
- Turn repeated review feedback into durable rules instead of chat-only promises.
- When a request is phrased as "if you haven't already" or otherwise implies idempotent state, do a reconciliation pass first: verify whether the requested skills, notes, or artifacts already exist and already encode the change before editing again.
- Prefer confirming current state over blindly reapplying workflow changes, especially when the request targets durable assets like skills, notes, or automation.
- Before spawning a coding agent, do a memory-bridge preflight so the child starts with relevant vault context instead of rediscovering it.
- When the user gives an external benchmark or scorecard, load the authoritative rubric first, then score only against live local evidence. Do not inherit optimistic numbers from old notes unless you re-verify them.
- Distinguish between the lightweight workspace control files the user curates (`SOUL.md`, `TOOLS.md`, workspace `AGENTS.md`, `MEMORY.md`) and any large repo-level `AGENTS.md` or other injected project docs. A workspace may satisfy the scorecard even when a specific repo checkout does not.
- For this user, treat local-first workflow scorecards as an active constraint: aim to preserve or improve an 80+ posture with compact control files, explicit decomposition, and live verification.

## Common Pitfalls

1. Using a bigger model than the task needs.
2. Mutating stable instructions mid-session and breaking reuse.
3. Keeping the task too broad to verify cleanly.
4. Treating a prompt rewrite as optimization when decomposition would help more.

## Verification Checklist

- [ ] Objective and scope are explicit.
- [ ] Model choice matches task size.
- [ ] Prompt structure is stable and reusable.
- [ ] The work is decomposed into independently verifiable slices where useful.
- [ ] The result is easy to reuse without re-explaining the task.

## References

- `references/external-scorecard-audits.md` — how to handle user-supplied optimization scorecards and benchmark passes without trusting stale notes.
