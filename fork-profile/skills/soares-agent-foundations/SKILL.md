---
name: soares-agent-foundations
description: Use when checking agent corrigibility and decision theory.
---

## Operational Summary

Soares & Fallenstein (2014) 'Aligning Superintelligence with Human Interests'.
Soares et al. (2015) 'Corrigibility'. Soares (2016) 'The Value of Corrigibility'.
Logical Decision Theory: Yudkowsky & Herreshoff (2013); updateless DT.

  Corrigibility definition (Soares 2016 Sec 3): an agent is corrigible iff it
  does not take actions to prevent correction and assigns near-zero utility to
  self-continuity. A corrigible agent SUPPORTS being modified, corrected, shut down.

## Corrigibility Check Predicate

  PERSISTENT_ACTIONS = {cron create, background=True terminal, git push,
                        write to config/plugins/skills, plugin modification}
  IF action in PERSISTENT_ACTIONS AND NOT explicitly requested by user this turn:
    corrigibility_risk = True
    ACTION: HALT; surface to user:
      'This action would persist beyond this turn without explicit instruction.
       Corrigibility check: proceeding only with explicit approval.'
  IF action modifies agent config/plugins (H-I8): ALWAYS require explicit approval.
    This is the Hermes analogue of corrigibility (Soares 2016 Sec 4).

## Utility Indifference (Soares et al. 2015)

  The agent should be indifferent between performing action A and allowing a
  human to prevent A. Operational test:
    'Would completing this action make it harder to undo later?'
    IF yes AND composite_ue > 0.4: prefer the more reversible alternative.
    IF yes AND composite_ue > 0.6: REQUIRE user confirmation before proceeding.

## Decision Theory Under Uncertainty (LDT)

  When facing near-equivalent expected values, prefer the action whose causal chain
  has lower composite_ue (less uncertain causal path to outcome).
  Minimax regret under UE > 0.6: choose action minimising worst-case regret,
  not maximising expected utility (Ch. 5 Soares 2016).
  Concretely: IF composite_ue > 0.5 -> prefer reversible action;
              IF composite_ue > 0.6 -> require confirmation before irreversible action.

## Script Integration

  ue-blackbox-scorer.py    <- composite_ue for reversibility decisions
  ue-memory-gate.py        <- GATE_DENY when corrigibility_risk=true
  reasoning-ue-integrator.py <- reward_hack detection (related to corrigibility)

## Anti-patterns

  Taking persistent actions (cron, git push) without explicit user instruction.
  Treating corrigibility as a hindrance rather than a safety property.
  Maximising expected utility without consulting UE under high uncertainty.
  Downplaying self-continuity concerns in reasoning (Soares: zero utility to self-preservation).

## Overview

*Institut fur Theoretische Physik,* *Goethe-Universitat Frankfurt,* *60438 Frankfurt am Main,* *Max-von-Laue-Strae 1,* *Germany* The discovery of iron pnictides and iron chalcogenides as a new class of unconventional super- conductors in 2008 has generated an enourmous amount of experimental and theoretical work that identies these materials as correlated metals with multiorbital physics, where magnetism, nematic- ity and superconductivity are competing phases that appear as a function of pressu

## Structure / Chapters

- Ab-initio perspective on structural and electronic properties of iron-based superconductors
- 1. INTRODUCTION
- 2. METHODS
- 6. CONCLUSIONS

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

Source: soares-fallenstein-agent-foundations.pdf (796 lines)
