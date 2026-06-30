---
name: dispatching-parallel-agents
description: Use when there are multiple independent investigations or implementation tasks that can be delegated concurrently.
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [subagents, delegation, parallelism, orchestration]
    related_skills: [using-superpowers, subagent-driven-development, autonomous-ai-agents]
---

# Dispatching Parallel Agents

Use one subagent per independent problem domain.

If the task is broadly about multi-agent orchestration and it is not yet clear which specialized agent/orchestration skill applies, load `autonomous-ai-agents` first as the router skill, then follow it to the right child skill.

## Good fit

- different failing test files with unrelated causes
- separate subsystems
- independent research tracks
- parallelizable verification work

## Bad fit

- shared mutable state
- overlapping file edits without coordination
- tasks that require the full parent context

## Hermes process

1. Partition the work into independent domains.
2. Give each subagent a self-contained goal, context, constraints, and expected output.
3. Launch them in a single `delegate_task(tasks=[...])` batch when possible.
4. Independently verify any claimed side effects before reporting success.

## Prompt pattern

Each child prompt should include:
- exact scope
- relevant files/errors
- hard constraints
- expected return format
- required language/tone if non-default

For implementation-heavy parallel work, prefer `subagent-driven-development`.
For role-selection or orchestration-pattern questions, prefer `autonomous-ai-agents` followed by `hermes-role-pipelines`.