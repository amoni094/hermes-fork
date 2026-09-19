---
name: kreyszig-functional-analysis
description: "Use when bounding approximation error in skill retrieval."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [functional-analysis, operator-norms, banach, contraction, error-bounds]
    related_skills: [luenberger-vector-space-optimization, boyd-convex-optimization, hastie-esl, hermes-context-budgeting]
triggers:
  - operator norm approximation error
  - Banach contraction refinement convergence
  - iterative refinement convergence bound
  - skill routing stability
  - Riesz representation embedding
  - functional analysis Kreyszig
  - bounded linear operator LLM
---

# Kreyszig Functional Analysis — Hermes Applications

Source: E. Kreyszig, *Introductory Functional Analysis with Applications* (Wiley, 1978).
Book: /var/home/rainbow/books/functional-analysis/kreyszig-functional-analysis.pdf


## Model Routing

Dense functional analysis reference lookup (no tool calls): deepseek-v4-pro non-think session. Implementation (approximation, error bounding code): grok-4.6 workers via delegate_task.


## 1. Banach Fixed Point Theorem — Refinement Convergence Bound (Ch 5)

If T: X -> X is a contraction (||T(x) - T(y)|| <= k*||x-y||, k < 1), it has a unique fixed point and x_{n+1} = T(x_n) converges from any start. A priori estimate: after n steps, ||x_n - x*|| <= k^n/(1-k) * ||x_1 - x_0||.

Hermes application: an iterative refinement loop converges iff each step brings output strictly closer to target by factor k < 1. Check: if error[i]/error[i-1] >= 0.9 for 2 consecutive steps, convergence is too slow — change strategy (model, prompt, approach). Use the a priori bound to estimate required iterations before starting a long loop.

## 2. Operator Norm — Skill Routing Stability (Ch 2)

||T|| = sup_{||x||=1} ||T(x)|| bounds: ||T(x) - T(y)|| <= ||T|| * ||x - y||.

Hermes application: the skill router maps query -> skill. High operator norm = small query rewording causes large skill-selection change = fragile routing. If the same task phrased slightly differently loads a completely different skill, routing is unreliable at that point. Mitigation: load top-2 skills; if they differ substantially, flag routing ambiguity and fall back to loading both.

## 3. Riesz Representation — Embedding Similarity as Linear Functional (Ch 3)

Every bounded linear functional on a Hilbert space is an inner product. Corollary: TF-IDF scoring (unnormalized dot product) is a bounded linear functional of the query; cosine similarity is NOT linear (the denominator ||q|| makes it scale-invariant, not additive). The Riesz theorem bounds retrieval quality: if two skills have similar embedding representations, no linear query can reliably distinguish them. Hermes application: skill retrieval quality is bounded by the representational capacity of the embedding space. If two skills have small ||y_A - y_B|| in embedding space, no query phrasing can reliably distinguish them. Fix: add explicit disambiguation triggers to frontmatter, not better query phrasing.

## 4. Contraction and LLM Output Stability

LLM-as-editor is approximately contractive at temperature=0 for small prompt perturbations. At temperature > 0 or near a decision boundary, linearity fails and outputs can change discontinuously (non-contractive). Practical rule: temperature=0 and fixed system prompt for any call where output stability matters; treat temperature > 0 outputs as samples, not deterministic outputs.

## Transfer Conditions

Applies when: well-defined metric/norm on inputs and outputs, transformation approximately linear in the relevant neighborhood, error bounds needed. Do NOT apply when: space is small and combinatorial, non-linearity is the primary phenomenon (use strogatz-dynamical-systems instead).

## Pitfalls

- Banach fixed point requires k < 1 strictly; k ~= 1 gives very slow convergence (not divergence, but practically unusable)
- Operator norm bounds are worst-case; average-case may be much better
- Riesz representation requires Hilbert space; TF-IDF spaces are approximately Hilbert (check for proper L2 normalization)
- Open mapping theorem requires linear operators; LLMs are non-linear
