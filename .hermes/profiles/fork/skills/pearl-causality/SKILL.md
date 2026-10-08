---
name: pearl-causality
description: Use when detecting or gating causal claims in responses.
---

## Operational Summary

Pearl (2000/2009) Causality. Pearl & Mackenzie (2018) Book of Why.
Three rungs of causal ladder:
  Rung 1 OBSERVATIONAL: P(Y|X) — 'associated with', 'correlated', 'tends to'
  Rung 2 INTERVENTIONAL: P(Y|do(X)) — 'causes', 'leads to', 'results in', 'due to'
  Rung 3 COUNTERFACTUAL: P(Y_x|X'=x') — 'would have', 'if X had not'
  Shpitser & Pearl (2006) do-calculus completeness:
    P(Y|do(X)) identifiable from observational data iff no unblocked backdoor path.

## Causal Claim Detection Gate

  ALWAYS run causal-memory-annotator.py before committing responses with
  causal language to memory.

  Rung classification triggers via regex (inside causal-memory-annotator.py):
    Rung 2: {causes, leads to, results in, due to, because of, therefore, hence,
             thus, enables, prevents, increases, decreases, drives, triggers}
    Rung 3: {would have, had not, without X would, if X had not, counterfactual}
  Confound risk: if context mentions C that could cause both A and B in claim A->B,
    set CONFOUND_RISK=true (backdoor criterion, Pearl Ch. 3).
  Controlled experiment markers reduce confound penalty:
    {experiment, randomized, RCT, intervention, do(, placebo, double-blind}

## UE Thresholds (tighter than factual 0.75)

  Rung 1: composite_ue > 0.75 WARN, > 0.90 DENY (standard)
  Rung 2: composite_ue > 0.40 WARN, > 0.60 DENY
  Rung 3: composite_ue > 0.30 WARN, > 0.50 DENY
  + CONFOUND_RISK: warn threshold -= 0.05, deny threshold -= 0.05
  UE penalty (added to composite_ue): Rung2 +0.15, Rung3 +0.25, confound +0.20

## Decision Rules

  Before memory commit with causal language:
    Run: python3 causal-memory-annotator.py annotate --content TEXT
    If gate_action=WARN: annotate with require_review=true, causal_type
    If gate_action=DENY: block memory commit, surface reason to user
  D-separation check: if recursive-causal-explorer.py has a DAG for current
    context, check that A->B is not blocked by d-separation from confound C.
  Rung 2/3 claims in memory: add tags {causal_type, confound_risk, rung}.

## Script Integration

  causal-memory-annotator.py   <- Rung classification, confound detection, UE penalty
  ue-blackbox-scorer.py        <- base composite_ue before penalty
  ue-memory-gate.py            <- final GATE_DENY/WARN/PASS using adjusted UE
  recursive-causal-explorer.py <- causal DAG for d-separation checks
  reasoning-ue-integrator.py   <- causal_check_flagged predicate

## Anti-patterns

  Asserting Rung 2 (causes) from Rung 1 data (correlation).
  Ignoring confounders visible in context.
  Treating temporal succession as causation.
  Skipping causal-memory-annotator.py for responses with 'therefore'/'hence'.

## Overview

Mathematical/computational reference. See source PDF for full content.

## Structure / Chapters

- (see source PDF)

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

Source: Causality_ Models, Reasoning and Inference.pdf (0 lines)
