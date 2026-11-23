---
name: decision-centric-memory
description: Use when compressing agent memory. Keep decision distinctions, not descriptions.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - compressing or evicting agent memory
  - rate-distortion memory budget
  - DeMem / decision-centric compression
  - what to forget under a memory budget
  - NOT for token compaction of the current context window (use cliff-compaction)
metadata:
  hermes:
    tags: [memory, rate-distortion, compression, retrieval]
    related_skills: [hermes-memory-surface-selection, rate-distortion-context-budget, memory-retrieval-over-write]
---

# Decision-Centric Memory (DeMem)

Source: arXiv:2605.10870 — Remember the Decision, Not the Description.

## Overview

Memory is valuable because it preserves distinctions between histories that change the next action, not because it faithfully describes the past. Compress against decision distortion, not summary fidelity.

## Rule

When writing, retrieving, or evicting memories:

1. Ask: if two histories share this compressed state, would the agent choose different actions?
2. If yes, do not merge them — that is a decision conflict (the forgetting boundary).
3. If no, they may share a memory state under the current budget.

Do not rank memories by salience, recency, or summary quality alone.

## Procedure

1. Identify the decision the current turn must make (tool, file, next step).
2. Retrieve memories that split action choices, not memories that merely resemble the query.
3. When the budget is tight, drop description (prose, quotes, atmosphere) before dropping decision-relevant facts (paths, IDs, outcomes, constraints).
4. Only refine the memory partition when new data certifies a shared state would cause conflict — do not pre-split on every new fact.

## Pitfalls

- Descriptive compression (summarize everything) can merge histories that need different actions.
- Expensive write pipelines (fact extraction, session summaries) can discard the distinctions retrieval later needs.
- Recency/salience heuristics are not a substitute for the forgetting boundary.

## Verification

- [ ] Eviction kept at least one fact that would change the next tool/file choice
- [ ] Two conflicting user constraints were not collapsed into one summary sentence
