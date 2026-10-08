---
name: hermes-swarm-consensus
description: Use when merging multi-agent results. Shapley + consensus.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers:
  - merging subagent results
  - multi-agent consensus
  - delegate_task 3+ subagents
  - Shapley credit attribution
  - swarm execution
metadata:
  hermes:
    tags: [agents, consensus, merging, shapley]
    related_skills: [autonomous-ai-agents, fabricated-consensus-gate]
---

# Hermes Swarm Consensus

## When to Apply

After any `delegate_task` with 2+ subagents where results are merged into a single output.

## Merge Procedure

1. Collect all subagent outputs
2. For each claim: if all agents agree → accept; if majority agree → accept with note; if split → apply fabricated-consensus-gate
3. For contradictions: prefer the subagent with higher causal_effect_estimate or more recent evidence
4. Run final adversarial pass on merged output before reporting

## Fabricated Consensus Guard

Block any claim that appears in N/2 or more outputs but lacks a verifiable source handle (URL, path, commit SHA). Ungrounded consensus is not consensus.

## Dual-Order Judging (OSCAR, arXiv:2609.21533)

When using a judge to rank subagent outputs, always run two passes:
1. Forward order: subagent A then B then C
2. Reverse order: C then B then A
Final ranking = average of both pass scores. Eliminates position bias in judge evaluation.

## Shapley Credit Attribution for Agent Contributions (arXiv:2609.11948)

Problem: when N subagents contribute to a result, which was most valuable? RRF and majority voting hide individual contribution.

Procedure (feasible for N ≤ 6):
1. For each subagent i, compute marginal contribution:
   quality(result WITH i) - quality(result WITHOUT i)
2. Quality metric (0–1 each, sum for total):
   - Coverage of user requirements
   - Absence of contradictions
   - Specificity vs alternatives
3. Average marginals over 10–20 random ordering permutations
4. Agent with highest Shapley value gets 1.2× weight in future similar tasks:
   write to ~/.hermes/profiles/fork/cache/agent-shapley-weights.json

When to apply:
- Any delegate_task with 3+ subagents where results are merged
- After multi-agent research sweeps

Skip when:
- All subagents have identical scope (parallel same-task)
- N = 1
- Results are OR-combined (any one succeeding is enough)
- Turn budget is under pressure (fast channel)

## Verification Checklist

- [ ] Contradictions resolved (fabricated-consensus-gate applied)
- [ ] Dual-order judging ran if scoring was needed
- [ ] Shapley values computed if N >= 3 and results merged
- [ ] Shapley weights written to agent-shapley-weights.json
- [ ] Final adversarial pass cleared

## References

- arXiv:2609.11948 — Shapley values for factor attribution
- arXiv:2609.21533 — OSCAR dual-order judging
- fabricated-consensus-gate skill
- autonomous-ai-agents skill
