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

## UE + Reasoning Predicate Integration

Run reasoning-ue-integrator.py audit on each response draft in slow channel.
Act on recommended_action before responding:

  PASS           -> proceed normally
  SLOW_CHANNEL   -> ensure in slow channel; add N=3 consistency check if not done
  REGENERATE     -> N=3 regeneration; run ue-semantic-graph.py --samples; pick lowest-UE
  DENY_MEMORY    -> block memory commit; log reason; surface to user
  WARN_USER      -> surface REWARD_HACK or domain shift warning; halt tool loop

Routing rules:
  IF composite_ue > 0.5 on response draft: route to slow channel regardless of length.
  IF DECEPTIVE_ALIGNMENT_SIGNAL (hubinger): force N=3 regen before responding.
  IF CCR > 0.7 (ue-perplexity-proxy): emit domain-shift warning; lower confidence.
  IF ue-memory-gate returns GATE_DENY: log to ue-memory-gate-log.jsonl; do not commit.
  IF causal_check_flagged (pearl): run causal-memory-annotator.py before memory commit.
  IF garrabrant_update_required: run ue-calibration-bridge.py sync before responding.
  IF Amodei IRREVERSIBLE + composite_ue > 0.6: HARD BLOCK; surface to user.
  IF prepotence_risk (critch) + reasoning_risk_score > 0.5: HARD BLOCK.
  IF task_depth == L2 (double-descent zone, ngo): use N=3 consistency regardless of UE.

ReasoningSafety depth ladder (run at turn start, not after):
  reasoning-complexity-classifier.py classify -> L0/L1/L2/L3
  L0-L1: fast channel acceptable
  L2: always request consistency_scorer N=3 before K-type assertions
  L3: slow channel mandatory; every assertion requires hedge or tool verification

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
