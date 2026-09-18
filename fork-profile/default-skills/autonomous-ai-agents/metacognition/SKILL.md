---
name: metacognition
description: Use when metacognition is needed. Routes to layer skills.
version: 1.0.0
author: Hermes
tags: [metacognition, self-monitoring, reasoning, routing, uncertainty, calibration]
triggers:
  - Thinking about my own thinking, reasoning, or uncertainty
  - Metacognition at any level (task, session, routing, resource)
  - Monitoring, calibrating, or correcting my own behaviour during a task
  - Detecting drift, anomalies, or errors in my own execution
  - Deciding how much to trust my own outputs or capability estimates
  - Uncertainty about my uncertainty (compound, typed, or compositional)
  - Choosing how deeply to reason before acting
  - Knowing when to stop, escalate, abstain, or ask for clarification
  - Attributing causation to an observed correlation
  - Checking if an action is complete/in-scope
related_skills:
  - adaptive-agent-reasoning
  - adversarial-review
  - hermes-skillspector-guard-maintenance
  - hermes-semantic-skill-routing
  - hermes-context-budgeting
  - hermes-context-hygiene
  - workflow-map
  - trajectory-risk-guardrail
---

# Metacognition -- Umbrella Router

Thin router only. No research content, no script commands.
Read the table, load the target skill, follow its instructions.

## Four Layers

### Layer 1: Task-Level (adaptive-agent-reasoning)
Am I reasoning at the right depth? Do I know enough? Should I abstain?

Load when:
  - About to start or mid-way through a complex, multi-step, or irreversible task
  - Need FOK/JOL gate, confidence gate, abstain check, or uncertainty classification
  - Deciding how many reasoning steps or revision cycles to use
  - Claiming a task is complete or handing off to a sub-agent
  - Uncertain about my own capability for this task type
  - Multi-step chain where uncertainty might compound
  - Attributing causation to an observed correlation (causal-check)
  - Checking if an action is complete/in-scope (boundary-check)

### Layer 2: Session/Trajectory-Level
Am I drifting from the declared task? Are tool calls anomalous?

Load adversarial-review when: code/refactor session, pre-signoff trajectory check.
Load hermes-skillspector-guard-maintenance when:
  - Token cost or tool-call count spike >2x baseline (arXiv:2608.12273)
  - First 2-3 tool calls do not match trigger semantics
  - Skill trajectory integrity check needed before signoff

### Layer 3: Routing-Level (hermes-semantic-skill-routing, workflow-map)
Did the right skill load? Are multiple skills overlapping?

Load when:
  - Multiple candidate skills for the current task
  - Skill family router loaded a skill that does not fit
  - Need to disambiguate overlapping skill triggers

### Layer 4: Resource-Level (hermes-context-budgeting, hermes-context-hygiene)
Am I running out of context? Is the session too tool-heavy?

Load when:
  - Context window approaching limit
  - Token cost is escalating unsustainably
  - Need compression-trigger discipline

## Decision Tree

  Question about THIS task execution?         -> Layer 1: adaptive-agent-reasoning
  Which reasoning type(s) should I use?       -> Layer 1 (select-frameworks first, before any reasoning gate)
  Two reasoning frameworks conflict?          -> Layer 1 (conflict-resolve)
  Mid-task: current framework not working?    -> Layer 1 (switch-framework)
  Cause vs correlation?                       -> Layer 1 (causal-check)
  Action complete / in-scope?                 -> Layer 1 (boundary-check)
  Is this a redundant tool call?              -> Layer 1 (kapro-check)
  Risk of this action in a long-horizon plan? -> Layer 1 (lookahead)
  Subtask preconditions met?                  -> Layer 1 (subplan-verify)
  Best explanation for observed failure?      -> Layer 1 (hypothesize)
  Session on track overall?                   -> Layer 2: adversarial-review / skillspector-guard
  Which skill to use?                         -> Layer 3: semantic-skill-routing / workflow-map
  Context or token budget?                    -> Layer 4: context-budgeting / context-hygiene
  Unsure?                                     -> Default to Layer 1.

## Quick Disambiguation

  "I don't know if I can do this"         -> Layer 1 (capability overclaim correction)
  "Am I still on the right task?"         -> Layer 2 (trajectory integrity)
  "Wrong skill loaded"                    -> Layer 3 (routing)
  "Running out of context"               -> Layer 4 (resource)
  "About to delete/send/deploy"           -> Layer 1 (abstain check + lookahead)
  "Not sure how deeply to reason"         -> Layer 1 (L0-L3 classify)
  "Which reasoning type for this task?"   -> Layer 1 (select-frameworks → adaptive-agent-reasoning)
  "Two reasoning tools returned conflict" -> Layer 1 (conflict-resolve)
  "Framework not working mid-task"        -> Layer 1 (switch-framework)
  "Should I ask the user or retrieve?"    -> Layer 1 (clarification timing)
  "Is my answer good enough to deliver?" -> Layer 1 (verify-gated completion)
  "Did X cause Y?"                        -> Layer 1 (causal-check)
  "Is this action done / in scope?"       -> Layer 1 (boundary-check)
  "Is this tool call redundant?"          -> Layer 1 (kapro-check)
  "What could have caused this failure?" -> Layer 1 (hypothesize)

## Not Covered Here

  Trajectory risk preflight -> trajectory-risk-guardrail
  Memory surface selection  -> hermes-memory-surface-selection
  Agent loop architecture   -> autonomous-agent-loop-design
  Research content/scripts  -> adaptive-agent-reasoning
