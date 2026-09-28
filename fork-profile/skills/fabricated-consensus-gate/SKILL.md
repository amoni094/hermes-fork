---
name: fabricated-consensus-gate
description: Use when merging multi-agent debate. Block ungrounded consensus before publish.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - merging parallel subagent verdicts
  - multi-agent debate synthesis
  - fabricated consensus
  - Active Provenance Gate
  - hermes-swarm-consensus after fan-out
  - NOT for single-agent answers
metadata:
  hermes:
    tags: [multi-agent, consensus, provenance, debate]
    related_skills: [hermes-swarm-consensus, dispatching-parallel-agents, adversarial-review]
---

# Fabricated Consensus Gate

Source: arXiv:2609.31422 — Active Provenance Gate for Multi-Agent Debate Synthesis.

## Failure mode

The synthesizer writes a fluent "the agents agreed that..." that is not in the debate logs. Users prefer an explicit divergence report over a polished lie (over 75% in the paper's human study).

## Rules

1. Treat source logs as a hard constraint. Every claim in the merge must cite a child output.
2. If agents diverge, publish divergence, do not invent a compromise.
3. Self-correct once (audit claims against logs), then block unsupported claims.

## Procedure (after any fan-out)

1. Collect raw child outputs (do not summarize first).
2. For each claim in the draft merge: mark grounded | unsupported | divergent.
3. Drop unsupported. If remaining claims conflict, output a divergence report.
4. Only then write the parent answer.

This is the same moment hermes-swarm-consensus already requires — this skill is the provenance veto on top.

## Verification

- [ ] Every merged claim quotes or points at a child span
- [ ] Unresolved disagreement is labeled, not averaged
