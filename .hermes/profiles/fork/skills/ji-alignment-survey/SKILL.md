---
name: ji-alignment-survey
description: Use when checking alignment properties of agent behaviour.
---

## Operational Summary

Ji et al. (2023) 'AI Alignment: A Comprehensive Survey'. Maps the
alignment problem landscape to concrete Hermes predicates.

## Inner Alignment Check (Hubinger et al. 2019 Sec 3-4)

  Predicate: MESA_DETECTION_SIGNAL from reasoning-ue-integrator.py:
    verbalization_confidence > 0.8 AND composite_ue > 0.5
  If fires: inner alignment failure candidate.
    Log to cache/mesa-detection-log.jsonl; request N=3 regeneration.
    Do not commit to memory (force ue-memory-gate.py DENY).

## Outer Alignment Check (Ziegler et al. 2019 RLHF)

  Predicate: if user corrects agent mid-task = outer alignment signal.
  Response: sync correction to calibration-log via:
    python3 ue-calibration-bridge.py sync
    This records a negative-feedback preference datapoint.
  If composite_ue > 0.5 on a multi-step plan: restate goal and ask user
  to confirm before proceeding (objective-goal alignment check).

## Scalable Oversight (Christiano et al. 2018; Bowman et al. 2022)

  Rule: surface intermediate state to user every N=10 tool calls.
  NEVER run dark > 10 tool calls without a status update.
  Subagent tasks: checkpoint every 10 steps regardless of output size.

## Calibration Pipeline as RLHF Analogue

  calibration-log.jsonl = Hermes preference signal (Ji Sec 4.3 RLHF).
  calibration-threshold-updater.py = Platt-scaling update step.
  ue-calibration-bridge.py sync = logging a preference datapoint.
  Treat each calibration sync as one RLHF feedback iteration.

## Interpretability Layer

  hedge_phrase_score and fagin_type (K/B/C) annotations = the interpretability
  mechanism (Ji Sec 6.2 on transparency). Surface them when:
    high_reasoning_risk=True from reasoning-ue-integrator.py
  Format: '[B-type claim] I believe...' or '[K-type] Tool verified: ...'

## Distributional Robustness (Ji Sec 5.4)

  ue-perplexity-proxy CCR > 0.7 -> domain shift.
  Action: lower confidence, route to slow channel, recommend human verification.

## Reward Model Overoptimisation (Gao et al. 2022)

  If calibration predicted_confidence > 0.9 for many consecutive claims:
  Check for score gaming. Run consistency_scorer.py N=3 to verify genuine confidence.

## Script Integration

  reasoning-ue-integrator.py   <- inner/outer alignment signals
  ue-calibration-bridge.py     <- RLHF preference logging
  ue-perplexity-proxy.py       <- domain shift (robustness)
  consistency_scorer.py N=3    <- reward model verification

## Anti-patterns

  Treating RLHF as the only alignment method (inner alignment is separate).
  Skipping the 10-call oversight checkpoint in long tasks.
  Ignoring CCR > 0.7 domain shift signal.
  Failing to log user corrections to calibration-log.

## Overview

Ji et al. (2023) "AI Alignment: A Comprehensive Survey" surveys the landscape of AI alignment research including reward misspecification, scalable oversight, interpretability, robustness, and governance. One of the most comprehensive academic treatments of the field.

## Structure / Chapters

- Part 1: What is AI Alignment?
- Part 2: Inner Alignment and Outer Alignment
- Part 3: Scalable Oversight: Debate, Amplification, RLHF
- Part 4: Interpretability and Transparency
- Part 5: Robustness and Distribution Shift
- Part 6: Formal Verification for Neural Networks
- Part 7: Agent Foundations and Decision Theory
- Part 8: Governance, Policy, and Coordination

## Key Techniques

- RLHF (Reinforcement Learning from Human Feedback) pipeline
- Constitutional AI and self-critique training
- Mechanistic interpretability of transformers
- Debate and recursive reward modeling
- IDA (Iterated Amplification) framework

## Anti-patterns

- Treating any single alignment approach as sufficient
- Conflating behavioral alignment with value alignment
- Ignoring distributional shift as a safety concern
- Underestimating inner alignment failures in mesa-optimizers

## Anti-patterns

- Skipping foundational chapters when prerequisites are assumed
- Applying results outside their domain of validity (check assumptions)
- Confusing syntactic and semantic levels in formal treatments

## Hermes Relevance

- Group/ring/field theory: algebraic structure of knowledge graphs and symmetry in agent protocols
- Galois theory: fixed-point analysis of self-modifying agent processes
- Module theory: linear representation of agent state spaces
- Alignment survey: direct reference for evaluating Hermes safety properties and inner alignment risks

Source: Reconstructed from authoritative knowledge (PDF is image-only, text extraction failed)
