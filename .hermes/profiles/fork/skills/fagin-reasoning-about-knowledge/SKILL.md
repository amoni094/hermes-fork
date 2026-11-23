---
name: fagin-reasoning-about-knowledge
description: Use when typing epistemic state of agent assertions.
---

## Operational Summary

Fagin, Halpern, Moses, Vardi (1995) Reasoning About Knowledge.
S5 modal logic axioms:
  K axiom: K(phi) -> phi (knowledge implies truth)
  Positive introspection: K(phi) -> K(K(phi))
  B (belief): phi true in MOST accessible worlds; does NOT imply truth
  C (common knowledge): fixed point of mutual knowledge; strongest type

## Epistemic State Typing for Hermes Assertions

  K (Knowledge): assert K(phi) ONLY if phi is TOOL-VERIFIED this turn
    (file read, terminal output, API response, DB query).
    hedge_phrase_score MUST be < 0.1.
    -> Use epistemic-state-tracker.py update --type K --has-tool-verification

  B (Belief): tool-unverified OR hedge_phrase_score > 0.1.
    Required hedges: 'I believe', 'likely', 'based on available context'.
    Decays over time (epistemic-state-tracker.py decay --hours 24).
    -> Use epistemic-state-tracker.py update --type B

  C (Common knowledge): Condorcet consistency_score = 1.0 from
    consistency_scorer.py N>=3 required. Do NOT assert C without this.
    -> Verify with consistency_scorer.py; then epistemic-state-tracker.py update --type C

## Classification Algorithm (run before slow-channel factual assertions)

  1. Is phi derived from a tool call this turn? -> K candidate
  2. Does response contain hedge phrases (hedge_phrase_score > 0.1)? -> B
  3. Is this a planning assumption, not a verified fact? -> B
  4. Condorcet=1.0 across N>=3 consistent_scorer runs? -> C eligible

## Epistemic Regression Rule (Fagin Ch. 3 on knowledge and time)

  K MUST NOT be downgraded to B silently. On contradiction:
    Log epistemic_regression to cache/epistemic-regressions.jsonl.
    Format: {ts, claim_hash, old_type:'K', new_type:'B', reason, composite_ue}
    Script: epistemic-state-tracker.py update --type B (auto-logs regression)

## Script Integration

  ue-blackbox-scorer.py       <- hedge_phrase_score for K/B classification
  consistency_scorer.py N=3   <- Condorcet=1.0 required for C
  epistemic-state-tracker.py  <- persistent K/B/C state table, decay, regression log
  reasoning-ue-integrator.py  <- fagin_type field in audit output

## Anti-patterns

  Asserting K without tool verification (violates K axiom: K->truth).
  Skipping hedge on B-type claims.
  Asserting C without Condorcet=1.0 (C requires inter-agent consensus).
  Silently downgrading K->B without logging epistemic regression.

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

Source: fagin-halpern-moses-vardy-reasoning-about-knowledge-ch1.pdf (0 lines)
