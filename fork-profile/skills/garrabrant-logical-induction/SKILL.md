---
name: garrabrant-logical-induction
description: Use when calibrating beliefs under logical uncertainty.
---

## Operational Summary

Garrabrant et al. (2016) prove a computable market-based inductor P_n that assigns
probabilities to logical sentences and converges to calibrated beliefs.

  Theorem 4.3 (Calibration): for any efficiently computable trader, the inductor
    is calibrated — beliefs converge to truth values of decidable sentences.
  Theorem 4.9 (Unbiasedness): no efficiently computable trader can systematically
    profit — beliefs are fair (martingale property).
  Theorem 4.18 (Learning Pseudorandom Sequences): inductor learns any efficiently
    samplable distribution.

## Hermes Operational Mapping

  BELIEF_PRICE(claim) = 1 - composite_ue (from ue-blackbox-scorer.py cache).
  UPDATE_RULE: on contradiction in calibration-log, multiply price by 0.5;
    on confirmation multiply by 1.2; clip to [0,1].

  CALIBRATION_OBLIGATION (Thm 4.3):
    ANY response containing probability language ("X% chance", "likely",
    "probably", "almost certainly", "unlikely", "I believe") MUST trigger:
      python3 ue-calibration-bridge.py sync
    Failure = Theorem 4.3 violation (uncalibrated claim).

  Decision rules:
    IF prob language AND no calibration-log entry for query_hash:
      -> run ue-calibration-bridge.py sync; annotate 'CALIBRATING'
    IF predicted_confidence > 0.9 for same claim domain in calibration-log:
      -> verify with consistency_scorer.py N=3; Condorcet=1.0 required to hold >0.9
    IF claim contradicted >= 3 times in calibration-log:
      -> downgrade to B-type (belief); add hedge phrase
    After probability claim: update epistemic-state-tracker.py
      --domain <claim> --type B --confidence <1-composite_ue>

  Garrabrant vs UE: Garrabrant is the theoretical ideal (market converges to truth).
  composite_ue is the empirical approximation. ue-calibration-bridge.py is the
  computable analogue of the Garrabrant market (Platt-scaling = calibration step).

## Anti-patterns

  Asserting probability claims without syncing calibration bridge.
  Treating composite_ue < 0.2 as certainty (calibration is asymptotic, not finite-time).
  Conflating logical uncertainty (decidable claims) with empirical uncertainty.
  Skipping calibration sync for hedged language ('might', 'perhaps').

## Script integration

  ue-calibration-bridge.py sync      <- log observation to calibration pipeline
  ue-blackbox-scorer.py              <- get composite_ue = 1 - BELIEF_PRICE
  calibration-threshold-updater.py   <- Platt scaling update (Garrabrant market step)
  consistency_scorer.py N=3          <- Condorcet verification for high beliefs
  epistemic-state-tracker.py update  <- record K/B/C type after calibration

## Overview

We present a computable algorithm that assigns probabilities to every logical statement in a given formal language, and refines those probabilities over time. For instance, if the language is Peano arithmetic, it assigns probabilities to all arithmetical statements, including claims about the twin prime conjecture, the outputs of long-running computations, and its own probabilities. We show that our algorithm, an instance of what we call a *logical inductor*, satisfies a number of intuitive desi

## Structure / Chapters

- Logical Induction
- Abstract
- Contents
- 2 Notation
- 3 The Logical Induction Criterion 14
- 3. Recall that a sequence *x* is efficiently computable iff there exists a computable func-
- 4. The traders sketched here are optimized for ease of proof, not for efficiency—a clever
- Pn(φn) hnpn.
- Furthermore, if P∞(φn) .npn, then
- 4.3 Calibration and Unbiasedness

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

Source: garrabrant-et-al-logical-induction.pdf (3933 lines)
