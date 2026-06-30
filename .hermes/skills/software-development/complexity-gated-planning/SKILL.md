---
name: complexity-gated-planning
description: "Use lightweight planning for simple work and formal design/plan checkpoints only when complexity justifies them."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, complexity, design, workflow]
    related_skills: [workflow-map, plan, systematic-debugging, test-driven-development, isolated-workspace-preflight, subagent-driven-development]
---

# Complexity-Gated Planning

Use this skill when deciding how much planning or design ceremony a task needs before implementation.

Core rule: plan enough to reduce risk, but do not force heavyweight process onto simple work.

## Step 1: Check complexity signals

Count how many are true:
- multiple subsystems are involved
- requirements are unclear or partially conflicting
- external integrations or APIs are involved
- schema/data model changes are likely
- concurrency, background jobs, or statefulness matter
- more than about 4 files will likely change
- delegation to multiple workers is likely
- rollback/recovery would be non-trivial

## Step 2: Choose planning level

### Level 0 — Direct execution
Use when 0-1 signals are true.

Action:
- proceed without formal plan
- keep a short mental or todo-based checklist

### Level 1 — Short execution plan
Use when 2-3 signals are true.

Action:
- write a concise plan in-chat or in todo items
- identify main files, verification steps, and main risk
- no heavy design doc required

### Level 2 — Structured implementation plan
Use when 4-5 signals are true.

Action:
- use the `plan` skill or produce a structured written plan
- include approach, file targets, validation steps, and rollout/rollback notes if relevant

### Level 3 — Design-first checkpoint
Use when 6+ signals are true, or when architecture is ambiguous/high-risk.

Action:
- compare 2-3 viable approaches
- identify tradeoffs
- get user confirmation if the choice materially affects architecture, cost, or risk
- only then implement

## Requirements ambiguity rule

If requirements are ambiguous but retrievable, inspect first.
Ask the user only when the missing decision materially changes implementation.

## Delegation rule

If multiple workers will be used, planning level should usually be at least Level 2.
Workers need a compact, explicit task packet; do not rely on them to infer the architecture from scattered chat context.

## Output guidance

State the planning level and why.
Examples:
- "Planning level 1: small two-file change with one unclear edge case."
- "Planning level 3: touches auth flow, persistence, and a background job, so I’m comparing approaches before implementation."

## Pitfalls

- writing large formal plans for obviously small tasks
- skipping design discussion on architecture-changing work
- treating delegation as free even when no plan exists
- asking for confirmation before doing retrievable discovery
