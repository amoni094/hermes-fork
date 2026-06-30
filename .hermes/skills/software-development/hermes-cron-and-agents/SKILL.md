---
name: hermes-cron-and-agents
description: "Use when you need the Hermes guidance for bounded sub-agents, isolated worktrees, or durable cron jobs with clear deliverables."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, agents, subagents, worktrees, cron, scheduling]
    related_skills: [hermes-agent, hermes-workflow-optimization, hermes-coding-review-loop, hermes-observability-and-task-ledger]
---

# Hermes Cron and Agents

## Overview

Use this skill when the task is naturally decomposable or needs durable scheduling.

Bounded sub-agents are for parallel slices that can be verified independently. Cron jobs are for work that must run on a schedule even when the main session is idle.

## When to Use

- You can split research, implementation, or verification into separate slices.
- You need a bounded sub-agent with a narrow objective.
- You need isolated worktrees or separate sandboxes for parallel edits.
- You want a recurring job for maintenance, verification, research refreshes, or retention work.

## Agent Rules

- Give each agent only the context it needs.
- Keep each goal specific and small.
- Use worktrees or isolated sandboxes when edits could overlap.
- Verify each agent’s output independently before combining results.

## Cron Rules

- Make the job self-contained.
- Keep the schedule, prompt, and deliverable explicit.
- Use cron for durable scheduled work, not conversational back-and-forth.
- Prefer silent success for watchdog-style jobs.
- Keep delivery isolated when the output should not clutter the main session.
- Use the task ledger when the platform exposes one so long-lived work stays visible.
- Prefer event-driven sync over cron when file changes can be observed directly.

## Common Pitfalls

1. Spawning an agent for a task that is not actually decomposable.
2. Giving a child too much context and turning it into a duplicate parent.
3. Using cron for a one-off conversational reminder.
4. Scheduling a job without a clear output shape or verification path.

## Verification Checklist

- [ ] The task is decomposed only where it helps.
- [ ] Each agent goal is narrow and specific.
- [ ] Cron jobs are self-contained and durable.
- [ ] Delivery stays isolated when needed.
- [ ] Independent verification happens before combining results.
