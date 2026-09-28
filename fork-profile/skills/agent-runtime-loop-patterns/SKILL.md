---
name: agent-runtime-loop-patterns
description: Use when structuring agent turns. Fast-slow routing + loop.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - structuring agent turns
  - fast-slow routing
  - turn budget allocation
  - runtime loop design
  - agent execution patterns
metadata:
  hermes:
    tags: [runtime, agent, routing, performance]
    related_skills: [cliff-compaction, tool-schema-filter-first, autonomous-ai-agents]
---

# Agent Runtime Loop Patterns

## Core Loop

Each agent turn follows: receive → classify → retrieve context → execute → compress → respond.
Keep this loop tight: avoid retrieving context not needed for the current classify result.

## Fast-Slow Channel Routing (arXiv:2609.14680)

Route each incoming message to either the fast or slow channel before any tool calls.

Fast channel (< 2 tool calls total):
- Urgent user clarifications
- Binary yes/no decisions
- Simple factual lookups already in context
- Respond immediately without memory retrieval

Slow channel (3+ tool calls):
- Research tasks requiring web fetch or paper search
- Multi-step planning with dependencies
- Memory consolidation or skill creation
- Full context retrieval justified

Decision rule:
  if (user message words < 20)
     AND (no code block, file path, or function reference)
     AND (no question mark in message body):
    -> fast channel
  else:
    -> slow channel

Budget cap: slow-channel tasks may NOT consume > 70% of turn budget when fast-channel requests are pending.
If a slow task is in progress and a fast-channel message arrives, checkpoint the slow task, service the fast request, then resume.

## Turn Budget Allocation

- Filter tool schemas first (see tool-schema-filter-first skill) before any retrieval
- Context near limit: apply cliff-compaction before the next tool call, not after
- Never retrieve a skill you already loaded this turn

## Loop Exit Conditions

- Explicit user stop signal
- All subtasks in the SAGE hierarchy completed and merged
- Adversarial pass cleared (no medium/high findings)

## References

- arXiv:2609.14680 — Fast-Slow Communication with Endogenous Transport
- tool-schema-filter-first skill
- cliff-compaction skill
- autonomous-ai-agents skill
