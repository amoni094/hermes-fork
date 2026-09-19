---
name: luenberger-vector-space-optimization
description: "Use when allocating tasks across agents via duality."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [optimization, vector-space, duality, projection, multi-agent-allocation]
    related_skills: [boyd-convex-optimization, dispatching-parallel-agents, puterman-mdp]
triggers:
  - dual decomposition task allocation
  - Lagrangian multipliers agents
  - projection theorem assignment
  - separable optimization dispatch
  - Luenberger vector space
  - min-norm underspecified task
  - token budget constrained dispatch
---

# Luenberger Optimization by Vector Space Methods — Hermes Applications

Source: D.G. Luenberger, *Optimization by Vector Space Methods* (Wiley, 1969).
Book: /var/home/rainbow/books/optimization/luenberger-optimization-vector-space.pdf

Complementary to boyd-convex-optimization (numerical algorithms); Luenberger provides geometric and duality theory underlying those algorithms.


## Model Routing

Optimization derivation, duality, Lagrangian analysis: magistral-small-latest (mistral). Implementation: grok-4.6 workers via delegate_task.


## 1. Projection Theorem — Closest-Skill Assignment (Ch 3)

For closed convex C in Hilbert space H, every x has a unique nearest point P_C(x). Hermes mapping: when assigning tasks to agents, choose the agent whose skill-tag vector is closest to the task's required-skill vector (minimum-distance projection). Guaranteed unique when capabilities are additive and bounded. Wire: dispatching-parallel-agents shape selection.

## 2. Lagrange Multipliers — Budget-Constrained Dispatch (Ch 7-8)

For min f(x) s.t. g(x) = 0, the multiplier lambda is the shadow price of the constraint. Hermes mapping: when dispatching N agents under a token budget B, allocate more context to the bottleneck agent (highest lambda = highest quality degradation per token removed). Do NOT allocate context uniformly. Swap rule: if trimming agent A by 20% costs less quality than expanding agent B by 20% gains, make the swap. Wire: dispatching-parallel-agents Context Budget Gate.

## 3. Separability — Pre-Dispatch Independence Check (Ch 7)

Separable objective f(x) = sum(f_i(x_i)) can be solved per-subproblem independently. Hermes mapping: if any subtask writes to a resource another subtask reads, the problem is not separable — use ordered-dependency shape, not parallel-frontier. Check separability before dispatch, not at merge time.

## 4. Min-Norm Solutions — Underspecified Task Handling (Ch 6)

Underdetermined system: minimum-norm solution has smallest ||x||, found via pseudoinverse. Hermes mapping: when a task spec is ambiguous, produce the minimum-commitment interpretation (fewest additional assumptions). Flag underdetermination explicitly rather than silently filling in plausible defaults. Maps to ISA skill's spec-as-test-suite.

## Transfer Conditions

Applies when: tasks and capabilities representable as vectors in metric space, objectives additive across agents, constraints linear or convex. Do NOT apply when: quality is purely categorical (no metric), agent capabilities non-comparable across domains.

## Pitfalls

- Strong duality requires convexity; agent dispatch is combinatorial — treat Lagrangian bounds as heuristics only
- Projection theorem requires closed convex sets; capability sets are neither in general — analogy is structural
- Separability check must happen before dispatch, not discovered at merge time
