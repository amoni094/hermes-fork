---
name: multi-agent-scaling-steiner
description: "Use when sizing fan-outs. Steiner task-type scaling rules."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers: []
---

# Multi-Agent Scaling with Steiner Taxonomy

Source: arXiv:2609.31563 - Multi-agent Scaling Across Disjunctive and Compensatory Tasks.

## Core insight

Multi-agent scaling depends on task type. Steiner taxonomy applied to LLM agents:
- DISJUNCTIVE: solved if ANY agent succeeds. More agents = monotone improvement.
- COMPENSATORY: solved by average/vote. Diminishing returns after N=3.
- CONJUNCTIVE: ALL agents must succeed. More agents = hurts (weakest link).

## Decision rules

1. Classify task before sizing fan-out:
   - One correct answer needed -> DISJUNCTIVE -> spawn 3-5
   - Aggregate/vote answer -> COMPENSATORY -> spawn 3
   - All subtasks must succeed -> CONJUNCTIVE -> serialize, verify each

2. DISJUNCTIVE: spawn independently (no shared context), return first success.
3. COMPENSATORY: spawn 3, majority vote. Benefit plateaus at N=5.
4. CONJUNCTIVE: do NOT parallelize - a failed subtask fails the pipeline.

## Integration with dispatching-parallel-agents

Apply task classification BEFORE sizing fan-out in any delegate_task call.
