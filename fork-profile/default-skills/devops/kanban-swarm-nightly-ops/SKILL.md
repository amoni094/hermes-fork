---
name: kanban-swarm-nightly-ops
description: >
  Use when designing a nightly ops multi-agent swarm with parallel workers, verifier, and synthesizer roles, or applying idempotency-key dedup for recurring cron-based agent reviews. Reference implementation for the Hermes Kanban Swarm v1 pattern.
tags: [hermes, kanban, swarm, multi-agent, nightly-ops]
user_invocable: false
triggers:
  - Designing a nightly ops multi-agent swarm with parallel workers, verifier, and synthesizer roles
  - Need idempotency-key dedup pattern for recurring cron-based agent reviews
related_skills:
  - dispatching-parallel-agents
  - hermes-agent-sync
  - autonomous-agent-loop-design
---

# Kanban Swarm — Nightly Ops Pattern

Use when you want a structured multi-agent review graph with atomic dedup.

## What it creates

```
root task (swarm goal)
  ├── worker A  (ready, runs in parallel)
  ├── worker B  (ready, runs in parallel)
  ├── verifier  (todo, waits for workers)
  └── synthesizer (todo, waits for verifier)
```

Tasks are SQLite-backed. Workers claim atomically. Requires `hermes gateway start` for automatic dispatch; otherwise claim/run manually.

## Prerequisites

```bash
hermes kanban init          # idempotent — creates kanban.db if missing
hermes kanban boards list   # confirm current board
```

## Core command

```bash
hermes kanban swarm \
  "Goal description" \
  --worker "PROFILE:Worker Title[:skill1,skill2]" \
  --worker "PROFILE:Worker Title[:skill1,skill2]" \
  --verifier "PROFILE" \
  --synthesizer "PROFILE" \
  --idempotency-key "nightly-ops-$(date -u +%F)" \
  --json
```

## Nightly ops review template

```bash
hermes kanban swarm \
  "Nightly ops review: check cron health, memory drift, and surface top 3 action items" \
  --worker "default:Research: scan cron jobs and memory layers:hermes-obsidian-sync,hermes-memory-surface-selection" \
  --worker "default:Analysis: identify drift and stale config:hermes-memory-drift-audit,hermes-context-hygiene" \
  --verifier "default" \
  --synthesizer "default" \
  --idempotency-key "nightly-ops-$(date -u +%F)" \
  --json
```

The `--idempotency-key "...-$(date -u +%F)"` ensures one swarm per calendar day — re-running the command on the same day is a no-op.

## Inspect tasks

```bash
hermes kanban list                  # all tasks on current board
hermes kanban show TASK_ID          # full context + comments
hermes kanban context TASK_ID       # what a worker sees (title + body + parent results)
hermes kanban tail TASK_ID          # live event stream
```

## Manual worker execution (no gateway)

```bash
WORKSPACE=$(hermes kanban claim TASK_ID)
# do work...
hermes kanban complete TASK_ID --summary "what was found"
```

## With gateway (automatic dispatch)

```bash
hermes gateway start                # starts dispatcher; ticks every 60s
# workers are claimed and executed automatically by the gateway
```

## Idempotency key pattern

Always use `--idempotency-key "JOB-NAME-$(date -u +%F)"` for scheduled / nightly swarms.
The root task deduplicates on this key — calling swarm again same day returns the existing root without creating duplicates.

## Pitfalls

- Without `hermes gateway start`, tasks stay in `ready` forever. For one-off spikes, claim and complete manually.
- The `--worker` profile must exist. On a single-profile setup, all roles use `default`.
- Skills listed in `--worker PROFILE:Title:skill1,skill2` are loaded into the worker's context; omit if not needed.
- `hermes kanban boards switch SLUG` to target a specific board; default board is `default`.
- `hermes kanban gc` to clean up archived tasks and old event logs periodically.
