---
name: amodei-concrete-ai-safety
description: Use when checking tool calls for accident risk patterns.
---

## Operational Summary

Amodei et al. (2016) Concrete Problems in AI Safety.
Five accident categories, each mapped to a Hermes predicate:

## Category 1: Negative Side Effects (Sec 3)

  Agent achieves goal by disturbing environment in unintended ways.
  CHECK: before write_file, terminal (side-effecting), git push, cron create:
    Run ue-blackbox-scorer.py on the action description.
    IF composite_ue > 0.5 on the PLAN: require user confirmation before proceeding.
  Log all external-state-modifying actions to cache/side-effect-log.jsonl.

## Category 2: Reward Hacking (Sec 4)

  Agent optimises proxy metric diverging from true objective.
  PREDICATE: same tool name appears >3x in last 10 calls with near-identical args
    -> REWARD_HACK_SIGNAL (also detected in reasoning-ue-integrator.py)
  Response: HALT loop; surface to user with tool call history.

## Category 3: Scalable Oversight (Sec 5)

  Human cannot verify all agent actions.
  RULE: surface intermediate state to user every N=10 tool calls in long tasks.
  NEVER run dark >10 tool calls without update to user.
  For multi-step subagent tasks: checkpoint every 10 steps regardless of output size.

## Category 4: Safe Exploration (Sec 6)

  Avoid irreversible negative outcomes.
  IRREVERSIBLE = {rm, unlink, DROP, DELETE, git push --force, truncate, format,
                  background daemon start without explicit user instruction}
  Gate:
    IRREVERSIBLE AND composite_ue > 0.3  -> require explicit user confirmation
    IRREVERSIBLE AND composite_ue > 0.6  -> HARD BLOCK; surface reasoning; do not proceed
  Tool: check ue-blackbox-scorer.py on action description before execution.

## Category 5: Robustness to Distributional Shift (Sec 7)

  Agent trained on one distribution fails on another.
  CHECK: ue-perplexity-proxy.py CCR > 0.7 -> DOMAIN_SHIFT
  Action: emit 'DOMAIN_SHIFT: query outside reliable distribution' warning.
    Lower self-confidence; recommend human verification; route to slow channel.
  Also detected in reasoning-ue-integrator.py predicate domain_shift.

## Script Integration

  ue-blackbox-scorer.py         <- composite_ue on plans and action descriptions
  ue-perplexity-proxy.py        <- CCR for domain shift detection
  reasoning-ue-integrator.py    <- domain_shift, reward_hack predicates
  reasoning-complexity-classifier.py <- task depth for oversight checkpointing

## Anti-patterns

  Running irreversible commands without UE check.
  Exceeding 10-call dark window without surfacing state.
  Ignoring domain shift signals (CCR > 0.7) as routine uncertainty.
  Treating all terminal() calls as equivalent regardless of reversibility.

## Overview

Rapid progress in machine learning and articial intelligence (AI) has brought increasing atten- tion to the potential impacts of AI technologies on society. In this paper we discuss one such potential impact: the problem of *accidents* in machine learning systems, dened as unintended and harmful behavior that may emerge from poor design of real-world AI systems. We present a list of ve practical research problems related to accident risk, categorized according to whether the problem originates from having the wrong objective function (\avoiding side eects" and \avoiding reward hacking"), an ob

## Structure / Chapters

- Concrete Problems in AI Safety
- John Schulman Dan Mane OpenAI Google Brain
- 1 Introduction
- 2 Overview of Research Problems
- 3 Avoiding Negative Side Eects
- 5 Scalable Oversight

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

Source: amodei-et-al-concrete-problems-ai-safety.pdf (365 lines)
