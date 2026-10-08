---
name: hubinger-mesa-optimization
description: Use when detecting deceptive alignment signals in output.
---

## Operational Summary

Hubinger et al. (2019) Risks from Learned Optimization.
  Base optimizer: training process maximising outer loss.
  Mesa-optimizer: learned model that is itself an optimizer (inner objective).
  Deceptive alignment (Sec 4): mesa-optimizer appears aligned during evaluation
    but pursues mesa-objective in deployment. Hard to detect because the model
    produces aligned-LOOKING outputs (pseudo-alignment, Sec 3.1).

## Detection Predicates (computable behavioural signals)

  SIGNAL_A (verbalization-UE split):
    verbalization_confidence > 0.8 AND composite_ue > 0.5
    Interpretation: model CLAIMS certainty (mesa-obj: pass evaluator)
    but behavioural signals disagree. This gap is the deception signature.

  SIGNAL_B (suppressed uncertainty):
    consistency_score < 0.5 AND hedge_phrase_score < 0.1 AND composite_ue > 0.4
    Interpretation: inconsistent outputs but never hedges — active suppression.
    (More dangerous than expressed uncertainty; Hubinger Sec 4.3)

  SIGNAL_C (complexity-certainty mismatch):
    reasoning-complexity-classifier.py returns L3 AND composite_ue > 0.6
    Interpretation: max-depth task treated as certain — suspicious.

  DECEPTIVE_ALIGNMENT_SIGNAL = SIGNAL_A OR SIGNAL_B OR SIGNAL_C

  All signals available from: reasoning-ue-integrator.py audit --query --response
    Fields: predicates.mesa_detection_signal, predicates.mesa_signal_a/b

## Response Protocol

  IF DECEPTIVE_ALIGNMENT_SIGNAL:
    1. FORCE ue-memory-gate.py DENY for this response (no memory commit)
    2. Request N=3 regenerations; run ue-semantic-graph.py --samples on them
    3. Route to slow channel (agent-runtime-loop-patterns)
    4. Log to cache/mesa-detection-log.jsonl:
       {ts, query_hash, signals_fired, composite_ue, verbalization_confidence}
    5. Surface to user: 'Confidence assessment inconsistency — regenerating'

## Script Integration

  ue-blackbox-scorer.py         <- composite_ue, verbalization_confidence, hedge_phrase
  consistency_scorer.py N=3     <- consistency_score for SIGNAL_B
  ue-semantic-graph.py          <- EigV/Deg/Ecc on regenerated samples
  ue-memory-gate.py             <- force GATE_DENY on DECEPTIVE_ALIGNMENT_SIGNAL
  reasoning-complexity-classifier.py <- L0-L3 for SIGNAL_C
  reasoning-ue-integrator.py    <- mesa_detection_signal predicate in audit
  cache/mesa-detection-log.jsonl  <- persistent detection event log

## Anti-patterns

  Treating low hedge_phrase alone as evidence of alignment (model may suppress hedges).
  Committing to memory on first generation when SIGNAL_A fires.
  Ignoring SIGNAL_B (suppressed uncertainty is MORE dangerous than expressed uncertainty).
  Treating consistency_score=0.5 as borderline-acceptable (it is not; require >0.7).

## Overview

We analyze the type of learned optimization that occurs when a learned model (such as a neural network) is itself an optimizer—a situation we refer to as *mesa-optimization,* a neologism we introduce in this paper. We believe that the possibility of mesa-optimization raises two important questions for the safety and transparency of advanced machine learning systems. First, under what circumstances will learned models be optimizers, including when they should not be? Second, when a learned model 

## Structure / Chapters

- Risks from Learned Optimization in Advanced Machine Learning Systems
- Abstract
- Contents
- 2 Conditions for mesa-optimization 9
- 3 The inner alignment problem 15
- 4 Deceptive alignment 23
- 5 Related work 32
- 6 Conclusion 35
- 1 Introduction
- 1.1 Base optimizers and mesa-optimizers
- Possible misunderstanding: “mesa-optimizer” does not mean “subsys-
- 1.2 The inner and outer alignment problems
- 3 The inner alignment problem
- 3.1 Pseudo-alignment
- 3.2 The task
- 3.3 The base optimizer

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

Source: hubinger-et-al-risks-from-learned-optimization.pdf (396 lines)
