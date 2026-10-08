---
name: hutter-aixi
description: Use when applying MDL/Solomonoff to selection.
---

## Operational Summary

Hutter (2004) Universal Artificial Intelligence: Sequential Decisions Based
on Algorithmic Probability. Consolidates Solomonoff induction + sequential DT.

  Theorem 5.32 (AIXI optimality): AIXI is Pareto-optimal in the class of all
    computable reward-bounded environments.
  Solomonoff prior: M(x) = sum_{p: U(p)=x} 2^{-|p|}. Weights explanations
    by their program length; shorter = higher prior (Occam's razor formalised).
  MDL (Rissanen 1978; Li & Vitanyi 1997 Ch.5):
    Prefer hypothesis H minimising |H| + |data|H|. Equivalent to MAP under
    Solomonoff prior.

## MDL Proxy Operations

  MDL proxy for response/explanation complexity:
    import zlib; len(zlib.compress(text.encode())) <- lower = simpler = higher prior

  CCR (Compression Complexity Ratio) from ue-perplexity-proxy.py IS the MDL proxy:
    CCR = zlib(query+response) / (zlib(query) + zlib(response))
    Lower CCR = response more predictable given query = lower description length.
    This directly approximates P(response | query) under Solomonoff prior.

## Decision Rules

  Skill routing MDL rule:
    When two skills match equally (same trigger score), route to the skill with
    shorter SKILL.md content (lower MDL = simpler description = higher prior).

  Model selection:
    Given two candidate explanations E1, E2, prefer the one with lower
    len(zlib.compress(E.encode())). Do not add complexity without evidence.

  AIXI utility under uncertainty:
    AIXI maximises sum_e M(e)*V(e) across all environments e weighted by M.
    When composite_ue is high, effective environment distribution is wider.
    Operational rule: IF composite_ue > 0.5 -> prefer action with higher floor
    value (maximin), not just maximum expected value.

  Sample efficiency (Solomonoff convergence rate = O(K(mu)) steps):
    For novel domains (CCR > 0.7), more samples required before confident assertion.
    Use consistency_scorer.py N=3 before asserting K-type in novel domains.

## Script Integration

  ue-perplexity-proxy.py     <- CCR as MDL proxy; domain novelty signal
  ue-blackbox-scorer.py      <- composite_ue for maximin decision rule
  consistency_scorer.py N=3  <- sample efficiency in novel domains

## Anti-patterns

  Preferring complex explanations when simpler ones are consistent with data.
  Ignoring CCR signal in model or skill selection.
  Not requesting N=3 samples when CCR > 0.7 (novel domain = more samples needed).
  Treating MDL as a soft preference rather than a hard routing rule.

## Overview

Sequential decision theory formally solves the problem of rational agents in uncertain worlds if the true environmental prior probability distribution is known. Solomonoff’s theory of universal induction formally solves the problem of sequence prediction for unknown prior distribution. We combine both ideas and get a parameter-free theory of universal Artificial Intelligence. We give strong arguments that the resulting AIXI model is the most intelligent unbiased agent possible. We outline how the AIXI model can formally solve a number of problem classes, including sequence prediction, strategi

## Structure / Chapters

- UNIVERSAL ALGORITHMIC INTELLIGENCE
- A mathematical top→down approach
- Marcus Hutter
- 17 January 2003
- Contents
- 1 Introduction
- 4.1 The Universal AIξ Model

## Key Techniques

- Core definitions, theorems, and proofs in the domain
- Algorithmic constructions with complexity and correctness analysis
- Worked examples connecting theory to computation

## Anti-patterns

- Applying asymptotic results outside their regime of validity
- Ignoring regularity conditions (measurability, compactness, smoothness)
- Treating proofs as implementation specs without realizability checks

## Hermes Relevance

Foundational reference for agent-system design:
- Memory/context: probability, IT bound compression and retrieval quality
- Routing: optimization and game theory guide skill selection policies
- Verification: formal methods and type theory ground safety arguments
- Coordination: mechanism design and session types model agent protocols
- Representation: category theory and topology structure knowledge graphs

Source: hutter-aixi-universal-ai.pdf (1138 lines)
