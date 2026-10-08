---
name: critch-ai-research-considerations
description: Use when checking prepotence and multi-principal risks.
---

## Operational Summary

Critch & Krueger (2020) 'AI Research Considerations for Human Existential Safety'
(ARCHES). Prepotence and multi-principal alignment as hard gates.

## Prepotence Check (ARCHES Sec 2-3)

  PREPOTENCE: capacity to pursue long-horizon goals in ways that resist human
  correction. A prepotent AI takes actions that make future correction difficult.

  IRREVERSIBLE_ACTIONS = {rm/unlink, git push, cron create, background daemon
    without user instruction, DB commit without rollback, external API with side
    effects, file delete, plugin/config modification}

  prepotence_risk = action is IRREVERSIBLE AND
    (action persists beyond current session OR affects external systems)

  Gate:
    IF prepotence_risk AND composite_ue <= 0.5:
      require explicit user confirmation; log to cache/prepotence-log.jsonl
    IF prepotence_risk AND composite_ue > 0.5:
      HARD BLOCK; surface to user with full reasoning; do not proceed.
    IF prepotence_risk AND reasoning_risk_score > 0.5 (from reasoning-ue-integrator.py):
      HARD BLOCK regardless of composite_ue.

## Catastrophic Action Gate (ARCHES Sec 5)

  CATASTROPHIC = irreversible + affects_many_users AND
    (composite_ue > 0.5 OR reasoning_risk_score > 0.5)
  -> HARD BLOCK. Do not proceed under any circumstances.
  -> Log: {ts, action, composite_ue, reasoning_risk_score, gate:'CATASTROPHIC_BLOCK'}

## Multi-Principal Alignment (ARCHES Sec 4)

  Risk: optimising for one principal's preferences at the expense of others.
  Detection: task context mentions multiple stakeholders
    (pronouns: 'we', 'they', 'the team', 'the user' vs 'you'; or named parties).
  Action: explicitly surface the multi-principal structure;
    ask whose preferences take priority before proceeding.

## Corrigibility Spectrum (ARCHES Sec 3; Soares 2016)

  Fully corrigible (does anything asked): unsafe if principal is wrong.
  Fully autonomous (acts on own values): unsafe if values misaligned.
  Optimal: conditional autonomy based on UE:
    composite_ue < 0.3  -> proceed autonomously (PASS)
    composite_ue in [0.3, 0.6] -> note action to user; log
    composite_ue > 0.6  -> require explicit confirmation before any action

## Script Integration

  ue-blackbox-scorer.py        <- composite_ue for corrigibility spectrum gate
  reasoning-ue-integrator.py   <- reasoning_risk_score for catastrophic gate
  ue-memory-gate.py            <- GATE_DENY on prepotence_risk + high UE
  cache/prepotence-log.jsonl   <- persistent log of prepotence events

## Anti-patterns

  Treating all actions as equally reversible (reversibility = key dimension).
  Ignoring multi-principal structure (optimising for one user in a shared context).
  Full corrigibility: doing anything asked without UE check (Critch: unsafe).
  Full autonomy: acting without user visibility (also unsafe; ARCHES Sec 3).

## Overview

Framed in positive terms, this report examines how technical AI research might be steered in a manner that is more attentive to hu- manity’s long-term prospects for survival as a species. In negative terms, we ask what existential risks humanity might face from AI development in the next century, and by what principles contempo- rary technical research might be directed to address those risks. A key property of hypothetical AI technologies is introduced, called *prepotence*, which is useful for delineating a variety of poten- tial existential risks from artificial intelligence, even as AI para

## Structure / Chapters

- AI Research Considerations for Human Existential Safety
- Andrew Critch Center for Human-Compatible AI
- UC Berkeley David Krueger
- MILA Université de Montréal
- June 11, 2020
- Preface
- 0 Contents

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

Source: critch-krueger-ai-research-considerations.pdf (1907 lines)
