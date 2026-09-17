---
name: complexity-gated-planning
related_skills:
  - workflow-map
  - plan
  - systematic-debugging
  - test-driven-development
  - isolated-workspace-preflight
  - subagent-driven-development
  - trajectory-risk-guardrail
  - mnemosyne-atp-safety

depends_on: [plan]
provides: [complexity-gated-planning, planning-decision, spike-or-plan]
triggers:
  - Deciding whether a task needs a formal plan or can be done directly
  - Implementation intent is known but plan-vs-direct-vs-spike ceremony is not
  - User wants planning discipline applied proportionally to task size
  - Checking if a spike, plan, or direct execution is the right first step
description: >
  Use when deciding how much planning a task needs (direct vs spike vs formal plan). Lightweight for simple work; design checkpoints only when complexity justifies them. Not for writing the plan file itself (use plan). Not for five-stage reasoning routing (use problem-solving-router).
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, complexity, design, workflow]
    related_skills: [workflow-map, plan, systematic-debugging, test-driven-development, isolated-workspace-preflight, subagent-driven-development, trajectory-risk-guardrail, mnemosyne-atp-safety]
---

# Complexity-Gated Planning

Use this skill when deciding how much planning or design ceremony a task needs before implementation.

Core rule: plan enough to reduce risk, but do not force heavyweight process onto simple work.

## Step 1: Check complexity signals

Count how many are true:
- multiple subsystems are involved
- requirements are unclear or partially conflicting
- external integrations or APIs are involved
- schema/data model changes are likely
- concurrency, background jobs, or statefulness matter
- more than about 4 files will likely change
- delegation to multiple workers is likely
- rollback/recovery would be non-trivial

**Description Complexity Gate (th-decomp2):** if zlib compression ratio of task description > 0.85 (high entropy = ambiguous task), escalate to FULL planning mode regardless of other signals.

## Step 2: Choose planning level

### Level 0 — Direct execution
Use when 0-1 signals are true.

Action:
- proceed without formal plan
- keep a short mental or todo-based checklist

### Level 1 — Short execution plan
Use when 2-3 signals are true.

Action:
- write a concise plan in-chat or in todo items
- identify main files, verification steps, and main risk
- no heavy design doc required

### Level 2 — Structured implementation plan
Use when 4-5 signals are true.

Action:
- use the `plan` skill or produce a structured written plan
- include approach, file targets, validation steps, and rollout/rollback notes if relevant

### Level 3 — Design-first checkpoint
Use when 6+ signals are true, or when architecture is ambiguous/high-risk.

Action:
- compare 2-3 viable approaches
- identify tradeoffs
- get user confirmation if the choice materially affects architecture, cost, or risk
- only then implement

## Pre-Execution Meta-Workflow

Before starting any task, run this gated sequence. Steps 2-4 are skipped for 0-1 signal tasks.

### Step 1: Size the task (signals above)
- 0-1 signals: direct execution — skip to step 5
- 2-3 signals: short plan
- 4+ signals: formal plan

### Step 2: Skill + session reuse check (2+ signal tasks only)
- Search skills and session_search for prior art
- Assess fit: does the skill address the primary failure mode or main integration point?
  - Yes = adapt it
  - Partial = note gaps and proceed
  - No match = proceed to step 3

### Step 3: Research optimal approach
Trigger: 4+ signals, OR 2-3 signals with no applicable skill found.
"Novel" = no skill covers the primary failure mode or main integration point.

- Time-box: one parallel tool-call batch (~5 minutes). No clear answer = pick simpler path and note uncertainty.
- 0-1 signal tasks never trigger this step regardless of skill availability.

### Step 4: Adversarial pass on the PLAN (not the implementation)
Run this loop:
1. Review the plan across all severity levels (correctness, gaps, contradictions, false claims)
2. Fix ALL findings — HIGH, MEDIUM, LOW — in the same pass
3. Re-read only the changed sections for immediate regressions
4. Run next pass on the full plan
5. Terminate when: a full pass produces zero HIGH/MEDIUM findings, then run one confirmatory pass

Additional rules:
- Low issues that cannot be fixed inline: log as a known limitation, do not block
- If the adversarial pass reveals the plan needs fundamental rethinking: re-enter at step 1 ONCE only
- Second fundamental failure = surface to user, do not loop again

### Step 5: Execute

### Step 6: verification-before-completion (ALWAYS — including 0-1 signal tasks)
- Requires fresh evidence: run it, read it back, check actual output
- Self-reported success from a subagent alone is not sufficient
- Stale output does not count as verification

## Goal-Driven Execution

Before starting any non-trivial task, transform it into verifiable goals. Weak criteria ("make it work", "improve this") require constant clarification. Strong criteria let you loop independently.

For multi-step tasks, state an explicit step→verify plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Examples:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

These guidelines are working if: fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come BEFORE implementation rather than after mistakes.

## Behavioral rules (think before coding)

Regardless of planning level, apply these before writing any code:
1. Think first — state the approach in a sentence or two before opening any file.
2. Keep it simple — prefer the fewest moving parts that satisfy the requirement; don't add abstractions speculatively.
3. Make surgical changes — touch only the files and lines needed; avoid reformatting or refactoring unrelated code in the same change.
4. Stay focused — finish the stated task before expanding scope, even if you spot nearby improvements.

Violation pattern: agent rushes in, touches many files, adds unused abstractions, reformats everything, and drifts from the original goal. These four rules are the fix.

## Grill-me: requirements interview before coding (Level 2+)

When planning level is 2 or 3, or when requirements are vague, run a brief requirements interview before writing code:
- Ask what the user is actually trying to accomplish (not just implement).
- Clarify success criteria and constraints.
- Surface any implicit assumptions that would change the approach.
- Optionally produce a short shared-language doc (see below) before starting.

Grilling mechanics (how to run the interview):
- Ask ONE question at a time. Asking multiple questions at once is bewildering.
- For each question, provide your own recommended answer before the user responds.
- Walk down each branch of the decision tree, resolving dependencies between decisions one by one.
- If a question can be answered by exploring the codebase, explore the codebase instead of asking the user.
- Continue until every branch of the decision tree is resolved.

Do not skip the interview to "save time." Misaligned implementation wastes far more time than a 2-minute clarification.

## Requirements ambiguity rule

If requirements are ambiguous but retrievable, inspect first.
Ask the user only when the missing decision materially changes implementation.

## Delegation rule

If multiple workers will be used, planning level should usually be at least Level 2.
Workers need a compact, explicit task packet; do not rely on them to infer the architecture from scattered chat context.

## Output guidance

State the planning level and why.
Examples:
- "Planning level 1: small two-file change with one unclear edge case."
- "Planning level 3: touches auth flow, persistence, and a background job, so I’m comparing approaches before implementation."

## Pitfalls

- writing large formal plans for obviously small tasks
- skipping design discussion on architecture-changing work
- treating delegation as free even when no plan exists
- asking for confirmation before doing retrievable discovery

## Phase Transitions in Constraint Satisfaction (arXiv:2608.12426, Sweep 15) ★ HIGH

LLMs handle individual constraints well but suffer **exponential collapse** in compositional
constraint regimes. CSE benchmark: 15 models, 36 constraint types, 369,753 checks at k=1–12.

**Three empirical findings:**

1. **Per-constraint pass rate decays gradually** — but their JOINT probability collapses.
   At k=8 simultaneous constraints: joint success rate ≈ 5.7% on average. <!-- why: individual constraint compliance is not predictive of joint compliance -->
2. **Structural constraints degrade ~2× faster** than lexical constraints under load.
   Structural = output format / schema / sustained-tracking constraints.
   Lexical = binary output decisions (word choice, tone) immune to composition effects.
3. **Failures are nearly independent** (multiplicative compounding). Model-specific failure
   rates multiply across constraints: `P(all pass) ≈ ∏ P(constraint_i passes)`.

**Hermes planning implications — add to Step 1 complexity signals:**

- Count simultaneous ACTIVE constraints in the task spec. Each of these is a constraint:
  - Output format requirements (JSON schema, specific structure)
  - Safety/scope restrictions (do not touch X, only use Y tools)
  - Stylistic requirements (concise, formal, cite sources)
  - Correctness gates (tests must pass, no regressions)
  - Temporal constraints (complete by, in order of)

  **7+ simultaneous constraints → Level 3 planning. 5–6 → Level 2.**
  This threshold is lower than the current complexity-signal count. <!-- why: joint failure is multiplicative, not additive -->

- For high-k constraint tasks: **the paper finds no ordering or selection of constraints
  mitigates the collapse at inference time** (pre-generation planning does not move the
  threshold at all; self-correction and best-of-5 retry delay collapse by only 1–2 constraints).
  The only effective mitigation is raising the per-constraint pass rate — i.e., decompose
  into fewer simultaneous constraints per step. <!-- why: paper explicitly shows no pairing/sequencing strategy helps; only decomposition works -->

- In delegation: when specifying task packets for subagents, do NOT enumerate more than 6
  simultaneous constraints in the `goal` field. Beyond 6: decompose into sub-tasks with
  at most 4 constraints each. <!-- why: subagent joint compliance at k>6 approaches chance -->

## Activation Bottlenecks — Constraints Known But Not Used (arXiv:2608.12321, Sweep 15) ★ MED

LLMs internally encode constraints at >88% probe accuracy but fail to route that knowledge
into decisions when a salient surface cue competes. This is a **routing problem, not a
knowledge problem** — the constraint is present but not activated at decision time.

**Two failure modes (from quartet diagnostic, 14 models):**
1. Repairable via activation patching (+6.4 nats) — constraint is encoded but suppressed
2. Not repairable by patching — encoding is corrupted by surface cue competition

**The only prompted mitigation that works: explicit prerequisite mention.** All other
interventions (rephrasing, chain-of-thought scaffolding) inflate conservative bias without
actually routing the constraint. Only explicitly naming the prerequisite dependency chain
before the decision reliably activates the constraint.

**Hermes planning implications:**

- When a task plan has an important constraint that MUST hold (safety rule, schema requirement,
  scope restriction), do NOT rely on the constraint being "in context" and assumed active.
  **Explicitly re-state the prerequisite dependency immediately before the decision step:**
  ```
  Before generating the output: the constraint is [X] because [prerequisite Y] applies.
  Now generate the output.
  ```
  This surfaces the dependency chain and activates the routing pathway. <!-- why: >88% of failures are routing failures, not knowledge gaps; prerequisite mention is the sole reliable fix -->

- This applies to ATP constraint checking too: when ATPGate.propose() evaluates a constraint,
  the constraint check_fn should include the prerequisite chain in its error message so the
  model can repair the proposal correctly:
  ```python
  ("tests_pass_before_deploy",
   lambda action, state: action["type"] != "deploy" or state.get("tests_pass"),
   "Cannot deploy: prerequisite is tests_pass=True (run tests first)")
  ```

- In delegate_task context: always include constraints AND their prerequisites in the `context`
  field, not just the goal. A subagent that "knows" the constraint from the goal alone will
  fail to activate it when a salient competing instruction is present. <!-- why: activation bottleneck is per-subagent; parent's encoding doesn't transfer -->

**Integration with fragility gate (ASMI):**
When a task has k ≥ 5 constraints AND a HAZARD-level step, the fragility gate must check
each structural constraint independently before proceeding — not just the overall task decision.

## Cognitive Load Signals for Planning Level (token-economics-skill-roi-scoring-2026.md, Jul 2026)

Raw token count is a poor proxy for reasoning quality. Use these instead:

- **Completion token count** is a reasonable proxy for *response* complexity — high completion
  tokens = model found it hard. Use as a signal to re-evaluate planning level after a task.
- **Dependency parse depth / clause count** in the request is a proxy for *input* complexity.
- **DTR (Deep-Thinking Ratio, arXiv:2602.13517):** proportion of tokens whose hidden-state
  distributions don't converge until deep layers correlates with accuracy on hard tasks.
  Long response ≠ high-quality reasoning. A short, decisive answer at depth is better.
- **Context Rot (Chroma):** LLM performance degrades non-linearly as input grows, independent
  of task complexity. For Level 2–3 plans: trim irrelevant files/tool outputs *before* the
  planning call to keep signal-to-noise high.
- **Effort routing:** Use `effort="low"/"medium"` for Level 0–1 tasks (Anthropic API);
  reserve `effort="high"` (default) for Level 2–3. (See anthropic-agent-api-patterns.)

## ASMI Fragility Gate for HAZARD-Level Steps (arXiv:2608.11138, Sweep 11)

ASMI (Attention-Subnetwork Mutual Information) shows that prediction confidence and prediction
fragility are ORTHOGONAL signals. A high-confidence answer can still be fragile — meaning
minor context changes would flip it. Standard confidence checks miss this entirely.

**Fragility gate (apply before any HAZARD-level action in the trajectory):**
1. Identify the key claim or decision gating the HAZARD step
2. Rephrase or reorder the top 2-3 context inputs and re-ask only the key question
3. If the answer changes structurally → **escalate**: require human confirmation or trigger verification-before-completion
4. If the answer is stable across rephrasing → proceed

**When to apply by planning level:**
- Level 0-1 tasks: skip (reversible, cost not worth it)
- Level 2 tasks with a HAZARD-level step: apply fragility gate immediately before the HAZARD
- Level 3 tasks: apply fragility gate after the design-choice step and before execution

**Pitfall:** Do not confuse output confidence with fragility. High confidence AND high fragility
can coexist — ASMI validates this is the norm, not the exception, for frontier LLMs on hard queries.

## ASMI Fragility Gate — Context-Adversarial Instability (arXiv:2608.11200) ★ MED — Sweep 11

ASMI (Adversarial Sensitivity to Minimal Inputs) shows that LLM decisions at HAZARD-level steps
are often fragile — minor context changes (reordering, rephrasing) flip the answer. Standard
confidence metrics miss this entirely.

The fragility gate above captures this. Additional guidance:
- **Fragility is worst on HAZARD steps that involve value judgments** (is this safe?
  is this the right approach?) vs factual lookups.
- **Re-run the gate on HAZARD steps that follow large context injections** (web_extract results,
  long file reads) — new context is the primary fragility trigger.
- **If fragility is detected: reduce context, not just the query.** The instability source is
  usually irrelevant content in the context window, not the question itself.

---

## Metacognition Handoff

After classifying a task (via complexity-gated-planning or
`reasoning-complexity-classifier.py classify --task "..."`):

1. Run select-frameworks with the SAME level classify just emitted. Do not
   recompute a second level by hand — `--level` is an override of classify_task(),
   not an independent scale.
   ```
   python3 ~/.hermes/scripts/reasoning-complexity-classifier.py classify --task "<task>"
   # take .level from that JSON (L0-L3), then:
   python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
     --task "<task description>" --level L2
   ```
   Omit `--level` to let select-frameworks call classify_task() itself (one source).
   L0-L1: exit 1 with empty primary and `"proceed": true` — this is NOT a failure.
   Do not treat `returncode != 0` as a crash. Exit 2 = real error (bad --level / empty --task).
   L2-L3: primary list drives which metacognitive gates to invoke (see adaptive-agent-reasoning).

2. If two frameworks return conflicting verdicts, run conflict-resolve before proceeding:
   ```
   python3 ~/.hermes/scripts/metacognitive-harness.py conflict-resolve \
     --framework-a '<framework-A>' --verdict-a '<PROCEED|BLOCK|UNKNOWN>' \
     --framework-b '<framework-B>' --verdict-b '<PROCEED|BLOCK|UNKNOWN>' \
     --task '<task description>' --confidence-a <0.0-1.0> --confidence-b <0.0-1.0>
   ```
   Exit 2 (both UNKNOWN): attended → requires_human=true, escalate. Unattended
   (`HERMES_UNATTENDED=1`, ralph-loops/cron): fail-closed skip this iteration — do
   not stall waiting for a human and do not invent a verdict.

3. Then load adaptive-agent-reasoning to apply FOK/JOL gates, confidence thresholds, and
   the full metacognitive entry-point flow, using only the frameworks from select-frameworks output.
