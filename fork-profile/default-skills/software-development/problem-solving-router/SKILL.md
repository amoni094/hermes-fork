---
name: problem-solving-router
description: "Use when a task is ambiguous across reasoning modes (debug vs plan vs research vs review) and you need the five-stage map. Not for writing a plan (use plan). Not for complexity-gating a known implementation (use complexity-gated-planning)."
version: 1.0.0
author: Hermes Agent
license: MIT
trust_level: trusted
tier: global
related_skills:
  - grill-me
  - complexity-gated-planning
  - workflow-map
  - ponytail-yagni
  - isa
  - plan
  - spike
  - systematic-debugging
  - trajectory-risk-guardrail
  - adversarial-review
  - risk-based-review
  - verification-before-completion
  - transfer-applicability-chain
metadata:
  hermes:
    tags: [reasoning, problem-solving, meta, routing, planning, verification]
---

# Problem-Solving Router

Meta-skill. Provides a common stage model and shared vocabulary that all
Hermes reasoning skills use, and routes to the right skill per stage.
Load this when a task is ambiguous or spans multiple reasoning modes.

Do NOT load this AND a specific stage skill in the same turn -- once routed,
load the target skill directly. This skill is the map, not the territory.

## Shared Vocabulary

These terms have consistent meaning across all Hermes reasoning skills.
When a specific skill uses them, this is what they mean.

  EVIDENCE       Tool output, file content, test results, command stdout/stderr.
                 Assertions, summaries, and LLM-generated text are NOT evidence.
                 "Fresh" = produced this session, not cached or assumed.

  DONE           Every claim about the outcome is closed by fresh evidence
                 of the right modality (file exists, test passes, URL responds).
                 "I think it worked" is not done. "236/236 exit 0" is done.

  REVERSIBLE     An action is reversible if its effect can be undone without
                 side effects on other systems. Git commits are reversible;
                 sent emails, published APIs, and deleted data are not.

  LOAD-BEARING   An assumption is load-bearing if the core mechanism fails
                 when the assumption is false -- not just degrades, but fails.
                 Disanalogies and feasibility gates target load-bearing assumptions.

  GATE           A hard stop. Pass = proceed; fail = stop and handle before continuing.
                 Gates are not suggestions. Partial pass is a fail.

  SKIP           Verdict meaning: do not implement, do not defer -- drop now.
                 Not the same as DEFER (requeue) or LATER (low priority).

  SPIKE          Throwaway experiment to establish feasibility. Time-boxed.
                 Output is a verdict (feasible / not feasible), not production code.
                 SPIKE verdict informs implementation; it does not replace it.

  STAGE          One of the five phases below. Stages are ordered but not always
                 all required -- skip stages that don't apply, never reorder them.

## Five Stages

### Stage 1 -- Frame
Understand the problem before touching anything.

Key questions:
  - What does done look like? (If unclear -> grill-me, then isa)
  - Is this the right problem? (If scope is fuzzy -> ponytail-yagni)
  - What must NOT be broken? (Name anti-claims before starting)
  - Is there an existing skill for this exact task? (Check skill list first)

Skills:
  grill-me            -- force sharp clarifying questions before starting
  isa                 -- define done as falsifiable claims before building
  ponytail-yagni      -- laziness ladder; 7 rungs before writing any new code

Gate: do not proceed to Stage 2 until done-criteria exist, even informally.

### Stage 1b -- Reasoning type selection (run after Frame, before Gate)

For any task that scored L2+ in Stage 1, determine which reasoning frameworks apply:
  ```
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<framed task description>" --level <L>
  ```
  L0-L1: no frameworks — proceed directly to Stage 3.
  L2-L3: primary list from output drives which metacognitive gates fire in Stage 2.
  If two frameworks later conflict, run conflict-resolve before continuing:
  ```
  python3 ~/.hermes/scripts/metacognitive-harness.py conflict-resolve \
    --framework-a '<framework-A>' --verdict-a '<PROCEED|BLOCK|UNKNOWN>' \
    --framework-b '<framework-B>' --verdict-b '<PROCEED|BLOCK|UNKNOWN>' \
    --task '<task description>' --confidence-a <0.0-1.0> --confidence-b <0.0-1.0>
  ```
  Exit 2 (both UNKNOWN) = escalate; do not invent a resolution.

### Stage 2 -- Gate
Check hard constraints before investing effort.

Key questions:
  - Is this reversible? (If not -> trajectory-risk-guardrail before acting)
  - Is this worth building at all? (YAGNI, complexity-gated-planning)
  - For research/findings: does this pass feasibility? (transfer-applicability-chain)
  - For dev tasks: what review depth does this deserve? (risk-based-review)

Skills:
  trajectory-risk-guardrail   -- pre-flight for irreversible/high-impact sequences
  complexity-gated-planning   -- right planning depth for the task size
  risk-based-review           -- how much review ceremony does this need?
  transfer-applicability-chain -- for findings/papers/tools: is this worth adopting?

Gate: irreversible or high-impact actions require trajectory-risk-guardrail clearance.
Gate: findings/papers require transfer-applicability-chain SPIKE verdict before implementing.

### Stage 3 -- Plan
Decide what to do and in what order before doing it.

Key questions:
  - Spike first or plan first? (spike for unknown feasibility; plan for known approach)
  - How much planning ceremony? (complexity-gated-planning output)
  - For dev: worktree isolation needed? (isolated-workspace-preflight)

Skills:
  spike           -- validate feasibility with a throwaway experiment
  plan            -- write .hermes/plans/<name>.md before execution
  workflow-map    -- choose the right dev workflow (TDD, subagent, dispatch, etc.)

Default: spike unknown feasibility first, then plan, then execute.
Do NOT plan and execute in the same mental step for anything non-trivial.

### Stage 4 -- Act
Execute the plan. Minimum viable surface area.

Key questions:
  - Is each step reversible before taking it? (if not, gate again)
  - Am I adding scope beyond the plan? (stop and re-run Stage 1)
  - For debugging: is the failure understood before fixing? (systematic-debugging)

Skills:
  systematic-debugging   -- 4-phase root cause before any fix attempt
  ponytail-yagni         -- if scope starts creeping during execution
  adversarial-review     -- for large/risky changes: cold review before merge

Rule: fix the root cause, not the symptom. Understand before changing.
Rule: if you are adding something not in the plan, stop. Re-run Stage 1.

### Stage 5 -- Verify
Produce fresh evidence that done-criteria are met before declaring complete.

Key questions:
  - Is there fresh evidence for every claim? (tool output, not assertion)
  - Has a cold path confirmed the result? (subagent or independent check)
  - For delegated work: did I verify the subagent's self-report? (never trust without checking)

Skills:
  verification-before-completion   -- require fresh evidence; never trust self-reports
  adversarial-review               -- structured cold review of large changes

Rule: a subagent claiming success is not evidence. Run the verification yourself
or dispatch an independent check with different context.
Rule: "it should work" is not done. Close every done-criterion with a tool result.

## Stage Selection Quick-Reference

Task type                           -> Start at stage
Fuzzy/ambiguous request             -> Stage 1 (grill-me + isa)
Known task, irreversible actions    -> Stage 2 (trajectory-risk-guardrail)
Known task, reversible, small       -> Stage 3 (complexity-gated-planning)
Bug / something broken              -> Stage 4 (systematic-debugging)
Claiming done / checking work       -> Stage 5 (verification-before-completion)
Paper / finding / tool to adopt     -> Stage 2 (transfer-applicability-chain)
Math/CS paper for Hermes            -> Stage 2 (math-cs-applicability-reasoning)

## What This Skill Is NOT

- Not a replacement for any specific skill -- load the target skill after routing
- Not a checklist to run on every task -- lightweight tasks skip most stages
- Not a process for its own sake -- stages exist to catch real failure modes,
  not to add ceremony. If a stage produces no signal, skip it.

## Relationship to Other Meta-Skills

  workflow-map            -- dev-specific routing (TDD, worktrees, subagents);
                             this skill routes to workflow-map for Stage 3 dev tasks
  complexity-gated-planning -- decides planning depth for Stage 3
  transfer-applicability-chain -- general findings evaluation for Stage 2
  math-cs-applicability-reasoning -- Hermes/math-CS papers specifically
