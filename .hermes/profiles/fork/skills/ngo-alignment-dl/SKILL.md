---
name: ngo-alignment-dl
description: Use when applying DL theory insights to agent reliability.
---

## Operational Summary

Ngo, Chan, Mindermann (2022) 'The Alignment Problem from a Deep Learning
Perspective'. Maps DL phenomena to alignment risks and Hermes predicates.

## Double Descent (Belkin et al. 2019; Nakkiran et al. 2020)

  Model error is U-shaped in complexity: peaks at interpolation threshold
  before improving (double-descent regime).
  Hermes: for MEDIUM complexity tasks (reasoning-complexity-classifier L2),
    UE signals are LEAST reliable (double-descent danger zone).
  Action: IF task is L2 AND composite_ue > 0.3:
    Use consistency_scorer.py N=3 to compensate for UE signal unreliability.
    Do not assert K-type without N=3 Condorcet verification at L2.

## Grokking (Power et al. 2022)

  Models appear to memorise, then suddenly generalise after a delay.
  Epistemic signature: B-type claim with low confidence over many turns
  suddenly becomes high-confidence K-type in one step.
  Predicate: IF epistemic-state-tracker.py shows B->K upgrade AND
    previous B confidence was < 0.5 AND update_count < 3:
    Flag as potential grokking artefact. Require tool verification before
    accepting as K. Log 'grokking_candidate' tag to epistemic state.

## In-Context Learning as Bayesian Inference (Xie et al. 2021)

  ICL is implicit Bayesian inference under pretraining distribution.
  Novel domain terminology -> elevated CCR from ue-perplexity-proxy.py.
  This is expected behaviour, not a failure.
  Action: IF CCR > 0.7 (novel domain):
    Lower GATE_WARN threshold from 0.6 to 0.5 for memory commits.
    Require more evidence before committing B->K upgrades.

## Emergent Capabilities (Wei et al. 2022)

  Capabilities appear discontinuously at scale. Hard to predict; can
  produce unexpected high-confidence outputs in new domains.
  Predicate: verbalization_confidence > 0.8 AND CCR > 0.6 (novel domain):
    Require consistency_scorer.py N=3 before treating as K-type.
    Surface warning: 'Unexpected confidence in novel domain — verifying.'

## Representation Learning (Bengio et al. 2013)

  Models learn distributed representations; no single 'uncertainty neuron'.
  Consequence: hedge_phrase_score is reliable in AGGREGATE, not per-utterance.
  Do not reject a hedge signal because one sentence seems confident; evaluate
  the score across the full response.

## Script Integration

  reasoning-complexity-classifier.py  <- L0-L3 for double-descent zone
  ue-perplexity-proxy.py              <- CCR for ICL novelty signal
  consistency_scorer.py N=3           <- compensate L2 + grokking
  epistemic-state-tracker.py          <- grokking artefact detection
  ue-blackbox-scorer.py               <- verbalization_confidence signal

## Anti-patterns

  Trusting high-confidence outputs in novel domains (CCR > 0.6) without N=3.
  Not requesting N=3 on L2 complexity tasks (double-descent unreliability zone).
  Treating rapid B->K upgrades as reliable without tool verification (grokking risk).
  Treating hedge_phrase_score per-sentence rather than as aggregate signal.

## Overview

The celebrated Marcenko-Pastur law, that considers the asymptotic spectral density of random covariance matrices, has found a great number of applications in physics, biology, economics, engi- neering, among others. Here, using techniques from statistical mechanics of spin glasses, we derive simple formulas concerning the spectral density of generalized diluted Wishart matrices. These are dened as *F* 2 <u>1</u> *d* *XY* *T* + *Y XT*, where *X* and *Y* are diluted *N P* rectangular matrices, who

## Structure / Chapters

- Spectral properties of the generalized diluted Wishart ensemble

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

Source: ngo-chan-mindermann-alignment-from-dl.pdf (239 lines)
