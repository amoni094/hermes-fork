---
name: hermes-observability-and-task-ledger
description: "Use when you need tracing, cost attribution, task-ledger discipline, or event-driven knowledge sync."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, observability, task-ledger, tracing, cost, latency, task-brain]
    related_skills: [hermes-agent, hermes-workflow-optimization, hermes-cron-and-agents, hermes-memory-capture-and-bridge]
---

# Hermes Observability and Task Ledger

## Overview

Use this skill when you need to know what agents are actually doing, how much they cost, or whether long-lived work is being tracked centrally.

The pattern is: measure first, use the task ledger as the source of truth for active work, and prefer event-driven sync over polling when files can notify you directly.

## When to Use

- You cannot easily tell why a run is slow, expensive, or wedged.
- You are running multiple agents or durable background tasks.
- You need a single control-plane view of long-lived work.
- You want knowledge updates to happen when files change rather than on a polling timer.

## Operating Rules

- Instrument before optimizing.
- Track latency, token usage, failures, and tool noise before changing the workflow.
- Use the task ledger for scheduled jobs, sub-agent spawns, and other long-lived work.
- When using Hermes shell hooks, `subagent_stop` is the low-friction event for appending child-run summaries into a local task-ledger JSONL stream.
- Prefer `hermes hooks list` and `hermes hooks doctor` to verify hook registration before assuming observability is live.
- Keep separate lanes for raw evidence, distilled conclusions, and action items.

## Observability First

Use native diagnostics first when available.

Look for:

- startup latency
- tool-surface noise
- stalled or wedged tasks
- cost hotspots
- failure patterns

Only add heavier tracing or dashboards if the native telemetry is not enough for the decision you are trying to make.

## Event-Driven Sync

If a knowledge graph or retrieval layer needs fresh file state, prefer filesystem events over cron polling.

Good pattern:

- file change
- short debounce
- hash / dedupe check
- upload or queue
- retry with backoff if the downstream service is down

Rules:

- do not poll if the OS can notify you directly
- keep the watcher self-healing and quiet when idle
- queue offline changes instead of losing them
- keep logs rotating and bounded

## Task Ledger Rules

- Treat the ledger as the control-plane view of durable work.
- Scheduled jobs and sub-agent runs should be visible there.
- Do not rely on chat transcripts as the only record of long-lived work.
- Keep follow-up tasks linked to the originating work when possible.

## Common Pitfalls

1. Optimizing before measuring.
2. Using cron for a file-change problem.
3. Grepping sessions instead of checking the task ledger.
4. Running too much observability before the native telemetry has been checked.

## Verification Checklist

- [ ] Costs, latency, failures, or tool noise were measured or inspected first.
- [ ] Long-lived work is tracked in the task ledger.
- [ ] File-change sync uses events, not unnecessary polling.
- [ ] Offline / failure behavior is defined.
- [ ] The output is still easy to reason about without a dashboard.
