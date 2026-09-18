---
name: adaptive-agent-reasoning
depends_on: [autonomous-agent-loop-design, complexity-gated-planning, hermes-context-budgeting]
provides: [reasoning-depth-allocation, test-time-scaling, self-correction-protocol, divergent-convergent-reasoning]
triggers:
  - Need to decide how much reasoning to allocate before a complex task
  - Planning how to use test-time compute for multi-step agent work
  - Implementing self-correction or critique-revision loops
  - Using multi-sample or branching strategies for hard tasks
  - Any agentic task where over-reasoning or under-reasoning is a failure risk
  - Uncertain, ambiguous, or missing evidence mid-task (uncertainty classification)
  - About to execute an irreversible action (delete, send, deploy, publish, pay)
  - Agent loop deciding when to stop iterating or how many revision cycles to run
  - Long multi-turn task where context budget or progress needs monitoring
  - Deciding whether and when to ask the user for clarification
  - Claiming or verifying that a task is complete
  - Multi-step chain where uncertainty might compound across steps
  - Estimating my own capability for a novel or out-of-distribution task
description: Use when allocating reasoning depth for agent tasks.
version: 1.0.0
author: Hermes
tags: [reasoning, test-time-compute, self-correction, adaptive, calibration]
related_skills: [autonomous-agent-loop-design, complexity-gated-planning, hermes-swarm-consensus, hermes-context-budgeting]
---

# Adaptive Agent Reasoning

Research-grounded protocol for right-sizing reasoning depth, correcting errors,
and allocating test-time compute in Hermes. Prevents two primary failure modes:

  - Over-reasoning: spending tokens on trivial tasks without accuracy gain
  - Under-reasoning: inadequate deliberation on complex/irreversible tasks

Key sources: arXiv:2608.20256 (adaptive mode learning), 2608.23956 (recursive
operators), 2608.15303 (divergent-convergent), 2606.05976 (self-correction
illusion), 2606.30005 (VISTA context dashboard), 2608.21265 (memory-augmented CoT).

---

## Consistency-Sampled Calibrated Confidence (Denuto Pattern)

Problem: LLM self-reported confidence is systematically overconfident (GPT-4 gave highest
confidence to 87% of responses including wrong ones).

**Solution**: Run N cheap re-verification calls on a small model, map agreement rate to
calibrated confidence. Source: Denuto `src/pipeline/consistency_scorer.py`.

**Theoretical basis**: Ensemble disagreement as uncertainty proxy (Lakshminarayanan et al.
2017, "Simple and Scalable Predictive Uncertainty Estimation"). N=3 with majority vote maps
to a Condorcet jury with p>0.5 competence. At p=0.7: P(majority correct) = 0.784 vs
individual 0.7 — modest improvement.

**Calibration mapping (conservative, not probability-theoretically derived):**

| Agreement | Calibrated Confidence |
|-----------|----------------------|
| 3/3 | 1.00 |
| 2/3 | 0.50 |
| 1/3 | 0.20 |
| 0/3 | 0.05 |

- Errors/null count as disagreement (conservative)
- Runs in parallel threads with timeout
- Feature-flagged, default-off (shadow mode before promoting)

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

def consistency_score(finding: str, verify_fn, n: int = 3, timeout: float = 10.0) -> float:
    """
    verify_fn(finding) -> bool: calls a cheap model with 'does this finding hold?'
    Returns calibrated confidence in [0.05, 1.00].
    """
    agreements = 0
    with ThreadPoolExecutor(max_workers=n) as executor:
        futures = [executor.submit(verify_fn, finding) for _ in range(n)]
        for f in futures:
            try:
                if f.result(timeout=timeout):
                    agreements += 1
            except Exception:
                pass  # errors count as disagreement
    mapping = {3: 1.00, 2: 0.50, 1: 0.20, 0: 0.05}
    return mapping.get(agreements, 0.05)
```

**Note**: 3/3→1.0 is epistemically overconfident — three independent llm-yes votes don't
prove truth. Treat as confidence signal, not ground truth. See `hermes-swarm-consensus`
for when to use this vs full consensus voting.

**GATE GAP**: No calibration logging in current implementation. To know if the mapping
is accurate, need to track (predicted_confidence, actual_correctness) pairs over time.

See also: `hermes-swarm-consensus`, `adaptive-agent-reasoning` § Adaptive Self-Consistency.

## Reasoning Frameworks Added (Sep 2026)

Six reasoning-type gaps were identified and implemented across two waves:

  CAUSAL      metacognitive-harness.py causal-check  (Pearl counterfactual + DCC)
  BOUNDARY    metacognitive-harness.py boundary-check (EBP scope/completeness)
  KAPRO       metacognitive-harness.py kapro-check   (K/A separation, -30% tool spam)
  LOOKAHEAD   working-memory.py lookahead             (FLARE terminal-risk scoring)
  SUBPLAN     working-memory.py subplan-verify        (HORIZON constraint gate)
  ABDUCTIVE   critique-bank.py hypothesize            (Peirce best-explanation)
  BACKWARD    working-memory.py plan-from-memory --backward-plan (goal→init)

Classifier auto-recommends frameworks via recommended_frameworks field:
  causal task  → ['causal-check']
  abductive    → ['hypothesize']
  long-horizon → ['lookahead', 'subplan-verify']

All wired into config.yaml under reasoning_frameworks + reasoning_hooks.
Research basis: arXiv:2605.25338, ACL2026 EBP, arXiv:2606.20661, arXiv:2601.22311,
arXiv:2604.11978, arXiv:2505.21935, arXiv:2411.01790, arXiv:2606.09863, arXiv:2608.30277.

## Config Key Reference

All metacognition behaviour is governed by documented `config.yaml` keys under
`reasoning_research.metacognitive_harness`. Those keys are policy defaults, not
runtime: scripts consume `MH_*` env vars only (see Subsystem Wiring).
Section names that are not H2s in this SKILL.md live in
`references/adaptive-reasoning-research.md` (extracted).
Key → governing rule mapping:

  fok_jol_enabled                                  → FOK/JOL Gate section
  jol_stop_threshold (default 0.8)                 → FOK/JOL Gate: deliver when JOL >= this
  fok_jol_gap_threshold (default 0.3)              → FOK/JOL Gate: retry when gap > this
  max_attempts_before_list_wise (default 2)        → FOK/JOL Gate: after N retries, use DCR blend
  confidence_gate.scope                            → Hard Confidence Gate: which task classes gate applies to
  confidence_gate.confidence_threshold (0.8)       → Hard Confidence Gate: threshold for FORCE_TOOL_CALL
  skill_profile.min_samples_before_delegating (5)  → Skill Profile: minimum history before blending
  skill_profile.blended_weight (0.5)               → Skill Profile: 50/50 verbal + empirical blend
  skill_profile.delegate_threshold (0.6)           → Skill Profile: delegate if blended < 0.6
  typed_uncertainty.enabled                        → Typed Uncertainty Gate section
  abstain_gate.enabled                             → Pre-Irreversible Abstention Gate section
  abstain_gate.confidence_threshold (0.8)          → Abstain Gate: abstain if confidence < this on irreversible actions
  abstain_gate.irreversible_keywords               → Abstain Gate: keyword list (overrides harness defaults)
  steer_conf.enabled                               → SteerConf Dual-Framing section
  steer_conf.level_gate (L2)                       → SteerConf: only apply at L2+
  reflection_loop.max_revision_cycles (2)          → CONFIRMED Early-Stop Sentinel: cap at 2 revisions
  reflection_loop.sentinel                         → CONFIRMED Early-Stop Sentinel: string that marks final answer
  compositional_uncertainty.enabled                → Compositional Uncertainty IU/EU section
  compositional_uncertainty.gate_threshold (0.4)   → IU/EU: abstain if compound EU > 0.4
  compositional_uncertainty.irreversible_weight    → IU/EU: weight for irreversible step uncertainty
  compositional_uncertainty.optional_weight        → IU/EU: weight for optional step uncertainty
  freshness.enabled                                → Claim Freshness & Temporal Decay section
  freshness.stale_threshold (0.5)                  → Freshness: decay score below this = re-verify
  freshness.half_lives_hours.prices_status (1)     → Freshness: prices/status half-life = 1h
  freshness.half_lives_hours.config_api (24)       → Freshness: config/API half-life = 24h
  freshness.half_lives_hours.code_docs (168)       → Freshness: code/docs half-life = 7 days
  freshness.half_lives_hours.identities (720)      → Freshness: identity facts half-life = 30 days
  freshness.half_lives_hours.constants             → Freshness: math constants never expire
  research_final_step.enabled                      → Final-Step JOL for Research section
  research_final_step.abort_on_mid_trajectory_low_confidence → Trajectory Confidence: false = replan, not abort
  research_final_step.restart_threshold_jol (0.7)  → Final-Step JOL: restart if final JOL < 0.7
  progress_gated_routing.enabled                   → Progress-Gated Routing section
  progress_gated_routing.escalate_on_stall         → Progress Router: escalate if stalled
  progress_gated_routing.stall_detection_steps (2) → Progress Router: stall = no progress in N steps
  planning.horizon_expand_max_steps (3)            → N/3 Horizon: max concurrent expand steps
  reasoning_frameworks.causal_reasoning.enabled           → Causal Reasoning Check section
  reasoning_frameworks.causal_reasoning.counterfactual_test → Causal: Pearl do-calculus prompt
  reasoning_frameworks.causal_reasoning.confound_check    → Causal: temporal/shared-driver/selection
  reasoning_frameworks.causal_reasoning.auto_trigger_on   → Causal: debugging, RCA, financial, scientific
  reasoning_frameworks.action_boundary.enabled            → Action Boundary Check section
  reasoning_frameworks.action_boundary.ebp_prompting      → Boundary: emit EBP block
  reasoning_frameworks.action_boundary.check_on_completion → Boundary: before claiming done
  reasoning_frameworks.action_boundary.check_on_verify_gate → Boundary: before verify-gate
  reasoning_frameworks.future_aware_planning.enabled      → Future-Aware Planning section
  reasoning_frameworks.future_aware_planning.lookahead_steps → Lookahead: projected-state count (default 3)
  reasoning_frameworks.future_aware_planning.trigger_on_irreversible → Lookahead: before delete/push/deploy
  reasoning_frameworks.future_aware_planning.trigger_on_horizon_gt → Lookahead: when steps > 5
  reasoning_frameworks.abductive_reasoning.enabled        → Abductive Hypothesis section
  reasoning_frameworks.abductive_reasoning.max_hypotheses → Hypothesize: --top default (3)
  reasoning_frameworks.abductive_reasoning.trigger_on_failure_mode → Hypothesize: constraint_skip/retry_loop/stale_assumption/false_attribution
  reasoning_frameworks.social_reasoning.enabled           → placeholder (false)
  reasoning_frameworks.ethical_reasoning.enabled          → placeholder (false)
  loop_harness.reasoning_hooks.pre_action_lookahead       → BEFORE IRREVERSIBLE: lookahead
  loop_harness.reasoning_hooks.pre_completion_boundary_check → AT COMPLETION: boundary-check
  loop_harness.reasoning_hooks.on_attribution_causal_check → MID-TASK: causal-check
  loop_harness.reasoning_hooks.on_failure_hypothesize     → MID-TASK: hypothesize
  reasoning_frameworks.reasoning_selection.enabled                → Reasoning Selection Protocol
  reasoning_frameworks.reasoning_selection.selector_subcommand    → select-frameworks (pre-task step 3)
  reasoning_frameworks.reasoning_selection.conflict_resolution.*  → conflict-resolve on contradictory verdicts
  reasoning_frameworks.reasoning_selection.dynamic_switching.*    → switch-framework on mid-task type shift

## Reasoning Selection Protocol

Meta-layer over existing frameworks. Classify complexity first, then select
which reasoning *type* to run — do not fire every framework on every L2+ task.
Rule/feature router (not an LLM self-route). Config keys are policy defaults;
scripts are opt-in CLI, not Hermes runtime.

Always at pre-task step 3, after classifier `classify`:

  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "TASK" [--context "..."] [--active-frameworks '[...]']

Exit: 0 = primary frameworks selected; 1 = none apply (trivial L0/L1); 2 = insufficient context.
Use `primary` now; keep `secondary` for if primary is inconclusive. Honor `exclude`.
Already-running names in `--active-frameworks` are omitted from `primary` (do not re-start them).
If `blend_strategy` is cascade and primary has >1 item, run in that order
(cheap/safety gates before slow explanation). Do not majority-vote disagreements.

When two primary frameworks disagree:

  python3 ~/.hermes/scripts/metacognitive-harness.py conflict-resolve \
    --framework-a A --verdict-a V --framework-b B --verdict-b W --task "TASK"

Exit: 0 = resolved; 1 = partial (low confidence / abstain+crux); 2 = escalate to human.
Same-class → confidence-weighted merge. Orthogonal (e.g. causal vs boundary) → cascade.
PROCEED vs BLOCK with confidence diff < 0.2 → abstain, isolate the crux — do not vote.
One UNKNOWN + other certain → trust certain. Both UNKNOWN → requires_human.

When the task type shifts mid-session (causal exhausted, now abductive; MixReasoning):

  python3 ~/.hermes/scripts/working-memory.py switch-framework --session SESSION \
    --from-framework causal-check --to-framework hypothesize \
    --trigger "root cause not found" [--prior-verdict UNKNOWN]

Carry still-valid conclusions; discard those the switch invalidates. Cap 3 switches/session.
Re-run select-frameworks on the remaining subtask (residual demand), not the original prompt.

Do not invoke extra slow frameworks to "be more careful about abstention" — more reasoning
can worsen abstention. Run abstain-check before slow frameworks on irreversible short-horizon tasks.

For L0/L1 queries (trivial/routine conversational), use the dedicated token-efficiency
layer BEFORE this skill: l01-token-efficiency. It provides a deterministic query gate,
Chain-of-Draft prompts, TALE-style budgets, Gricean Quantity blocks, and verbosity scoring
with no additional LLM calls. AdaCoT evidence: 96.82% of production traffic should NOT CoT.
Load adaptive-agent-reasoning only for L2+ (complex/critical) tasks.

## Master Metacognition Entry Point

Use this flowchart every time you load this skill. It tells you exactly which
scripts to call and in what order. All sections below provide the detail.

PRE-TASK (before first tool call):
  1. Knowledge boundary check (task-start):
       python3 ~/.hermes/scripts/working-memory.py plan-from-memory --session SESSION
       → retrieves prior analog trajectories; primes WM with constraint hints
  2. Self-modeling optimism correction (novel task? correct overclaim before starting):
       Mentally apply: verbal capability estimate is an upper bound; subtract 15-20%
       for novel types. For known types, blend with skill-profile empirical rate.
  3. Classify complexity, then select frameworks:
       python3 ~/.hermes/scripts/reasoning-complexity-classifier.py classify --task "TASK"
       python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks --task "TASK"
       → L0/L1/L2/L3; select-frameworks.primary is the type router (not the keyword list)
       → invoke primary scripts at the matching gates below; L2+ for causal/abductive signals
  4. FOK/JOL gate (L2+ only):
       python3 ~/.hermes/scripts/metacognitive-harness.py evaluate --fok F --jol J [--attempt N]
       exit 0 = STOP_AND_DELIVER  → proceed
       exit 1 = RETRY_WITH_FEEDBACK → revise understanding, re-evaluate
       exit 2 = ABORT_LIST_WISE    → use DCR blend (list-wise aggregation)
  5. Compositional uncertainty check (multi-step chains):
       Run IU/EU noisy-OR mentally; if compound EU > 0.4 → abstain or retrieve

BEFORE EACH IRREVERSIBLE ACTION (delete/send/deploy/publish/pay/write):
  6. Abstain check (confidence gate — not a substitute for lookahead):
       python3 ~/.hermes/scripts/metacognitive-harness.py abstain-check          --action "ACTION_DESCRIPTION" --confidence C
       exit 0 = PROCEED
       exit 4 = ABSTAIN_BEFORE_EXECUTING → stop; ask user or re-check
  6b. Lookahead (commitment / must-constraint gate; config: pre_action_lookahead):
       python3 ~/.hermes/scripts/working-memory.py lookahead --session SESSION --action "ACTION_DESCRIPTION"
       exit 0 = PROCEED, 1 = CAUTION (continue with recovery plan), 2 = BLOCK
       If classifier recommended_frameworks includes subplan-verify, also:
       python3 ~/.hermes/scripts/working-memory.py subplan-verify --session SESSION --subplan '[...]'

MID-TASK (after each tool result):
  7. Progress-gated routing: re-score plan vs result; if stalled 2+ steps → escalate
  8. Typed uncertainty (on failure/surprise):
       python3 ~/.hermes/scripts/metacognitive-harness.py typed-uncertainty          --description "AGENT_UNCERTAINTY_DESCRIPTION"
       → AMBIGUOUS_INPUT / MISSING_EVIDENCE / OUT_OF_SCOPE / TOOL_FAILED / UNKNOWN
       → each type has a bound action (clarify / retrieve / abstain / retry / manual)
  8b. Causal-check when attributing a cause (config: on_attribution_causal_check):
       python3 ~/.hermes/scripts/metacognitive-harness.py causal-check --observation "X" --candidate-cause "Y"
       exit 0 = CAUSAL, 1 = CORRELATED, 2 = UNKNOWN
  8c. Hypothesize on unexpected failure (config: on_failure_hypothesize):
       python3 ~/.hermes/scripts/critique-bank.py hypothesize --observation "X" --context "Y"
       exit 0; use hypotheses[].test_to_confirm before retrying
  9. Confidence gate (L2+ factual/irreversible claims):
       python3 ~/.hermes/scripts/metacognitive-harness.py gate          --confidence C --tool-called true/false [--level L2]
       exit 0 = PASS
       exit 3 = FORCE_TOOL_CALL → must verify with a tool before proceeding
  10. Hedge score (verbal outputs):
       python3 ~/.hermes/scripts/metacognitive-harness.py hedge-score          --reasoning "OUTPUT_TEXT"
       exit 0 always; check hedge_score field: > 0.4 = over-hedged, reframe

CLARIFICATION TIMING (when to ask user):
  11. Goal clarification: ask in first 10% of execution or skip entirely
      Input-slot clarification: ask up to ~50% of execution
      Past 50%: retrieve missing inputs rather than ask — UNLESS user-resolvable
      intent/constraint issue, in which case use 4-field escalation schema

AT COMPLETION:
  12. Boundary-check then verify-gated completion (config: pre_completion_boundary_check):
       python3 ~/.hermes/scripts/metacognitive-harness.py boundary-check --action "LAST_ACTION" --task "GOAL"
       exit 0 = COMPLETE, 1 = INCOMPLETE, 2 = OVER_ACTION, 3 = SCOPE_CREEP
       python3 ~/.hermes/scripts/working-memory.py verify-gate --session SESSION
       → for each stated constraint, is there tool-grounded evidence?
       → if any constraint has no evidence: do not claim done (fail-closed)
       → unresolved open questions are OK if annotated in the answer
  13. Reflection cap: max 2 revision cycles; after that, emit CONFIRMED + deliver best-current
  14. Calibrate classifier (L2+):
       python3 ~/.hermes/scripts/reasoning-complexity-classifier.py calibrate          --predicted L2 --actual L3
       → feeds accuracy tracking; run `stats` to check calibration health

HANDOFFS (multi-agent / multi-turn):
  15. Before handing off to a sub-agent:
       python3 ~/.hermes/scripts/working-memory.py handoff-export --session SESSION
       → exports constraints + WM state; sub-agent loads this as its starting context
  16. For skill routing decisions, emit compact WM snapshot:
       python3 ~/.hermes/scripts/working-memory.py skill-hint --session SESSION

EXIT CODE QUICK REFERENCE:
  metacognitive-harness.py evaluate: 0=STOP_AND_DELIVER, 1=RETRY, 2=ABORT_LIST_WISE
  metacognitive-harness.py gate:     0=PASS, 3=FORCE_TOOL_CALL
  metacognitive-harness.py hedge-score: 0 always (check hedge_score field)
  metacognitive-harness.py typed-uncertainty: 0 always (check uncertainty_type field)
  metacognitive-harness.py abstain-check: 0=PROCEED, 4=ABSTAIN_BEFORE_EXECUTING
  metacognitive-harness.py causal-check: 0=CAUSAL, 1=CORRELATED, 2=UNKNOWN
  metacognitive-harness.py boundary-check: 0=COMPLETE, 1=INCOMPLETE, 2=OVER_ACTION, 3=SCOPE_CREEP
  dcr-reconcile.py check/reconcile:  0=success, 2=error
  reasoning-complexity-classifier.py classify: 0 always (check level + recommended_frameworks)
  reasoning-complexity-classifier.py select-frameworks: 0=selected, 1=none apply, 2=insufficient context
  metacognitive-harness.py conflict-resolve: 0=resolved, 1=partial, 2=escalate to human
  working-memory.py switch-framework: 0=recorded, 1=max switches reached, 2=missing session/unknown framework
  working-memory.py verify-gate:     0=pass, 1=consecutive verify failures, 2=missing session
  working-memory.py lookahead:       0=PROCEED, 1=CAUTION, 2=BLOCK
  working-memory.py subplan-verify:  0=OK, 1=WARN, 2=BLOCK
  critique-bank.py hypothesize:      0=hypotheses_generated


## Step 0 -- Classify Task Complexity Before Reasoning

Run the complexity classifier BEFORE investing reasoning tokens:

  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py classify \
    --task "<task description>" --context "<relevant constraints>"

Output gives: level (L0-L3), budget_tokens, strategy, prompt_prefix.

  L0  trivial    direct     0       lookup, formatting, single-fact
  L1  routine    chain      300     standard task with known pattern
  L2  complex    reflect    1200    multi-step, tradeoffs, novel territory
  L3  critical   deliberate 3000    irreversible, high-stakes, production

Use the prompt_prefix from the output to prepend to the model call.

Do not skip classification for long chains of tool calls -- each subtask
may re-classify differently. A deploy step inside an L1 workflow is still L3.

---

## Reasoning Strategies by Level

### L0 -- Direct (no CoT)
Answer immediately. Inserting a reasoning prefix actively reduces accuracy on
straightforward factual retrieval (arXiv:2608.20256).

### L1 -- Chain (light CoT)
Short numbered steps. Do not elaborate past what is needed to execute.
Target: <=300 reasoning tokens.

### L2 -- Reflect (full CoT + critique)
1. State the problem precisely
2. Identify constraints and edge cases
3. Consider 2-3 approaches with tradeoffs
4. Select best with rationale
5. Execute with inline verification
6. Self-check: "Does the output satisfy the stated constraints?"

If prior similar tasks were stored as pattern cards in Hermes memory, inject
1-3 relevant cards as prefill before reasoning (arXiv:2608.21265 motivation;
note: paper's +21.4pp GSM8K / +28.0pp MATH are vs Chain-of-Draft compression
paths not implemented here -- treat as directional motivation, not a target).

### L3 -- Deliberate (full + adversarial self-check)
1. Restate task and confirm scope with user if ambiguous
2. List every irreversible action explicitly
3. Identify failure modes and rollback paths
4. Write the adversarial case: what specific ways could this go wrong?
5. Verify adversarial check passes before executing
6. Execute with checkpoints after each irreversible action
7. Log outcomes to working-memory for calibration

---

## Test-Time Compute Allocation (arXiv:2608.23956, 2608.15303, 2408.03314)

EMPIRICAL: BRANCH dominates (+5.98pp across 14 settings). GROW can hurt
(degrades on non-truncated tasks). Do NOT use GROW/PRUNE as default L2
operators; use BRANCH as the primary escalation path.

Three operators -- use only as indicated:

BRANCH (default for L2-L3, all hard tasks):
  - Spawn 2-4 independent attempts with distinct strategies (not paraphrases)
  - Reduce with list-wise judge or DCR reconciler (not majority vote)
  - Use: delegate_task with 2-3 children, distinct approach in each goal
  - +5.98pp averaged across 14 model-benchmark settings (2608.23956)
  - BRANCH gain correlates with truncation (r=0.72) but is beneficial even
    without truncation; this is the safe default.

GROW (fallback ONLY -- sequential revision when output is truncated):
  - Do not pre-allocate max tokens; extend on demand after actual truncation
  - DO NOT use as a routine L2 operator; paper shows it degrades on non-truncated tasks

PRUNE (structured decompose-recompose for multi-part problems):
  - Decompose into independent subproblems, solve in parallel, then recompose
  - Use: delegate_task fan-out + hermes-agent-sync merge
  - Only when subproblems are genuinely independent

Default routing (BRANCH is the default escalation path):
  L0-L1: NONE (single call)
  L2: BRANCH k=3 (default); GROW only if output was actually truncated
  L3: BRANCH k=5 + DCR reconcile + adversarial review

Divergent-Convergent Reconciliation (DCR) for BRANCH results:
  Phase 1 (Diverge): Generate 3 solutions with distinct strategies/framings
  Phase 2 (Converge): "Here are 3 candidate solutions: [A] [B] [C].
    They disagree on: <list specific disagreements>.
    Reconcile: select or synthesize the best with explicit evidence."

NOTE: The paper's 93.3% AIME / ~27% compute reduction is RECURSIVE DCR
(width K=8, unanimous-consent stop, dispersion-gated extra rounds). The
script (dcr-reconcile.py) implements the disagreement-detection and prompt
generation steps -- not the recursive multi-round reconcile. Label this as
"DCR-inspired" and do not cite the paper's numbers as a target.
(arXiv:2608.15303). Gate Phase 2 on actual answer disagreement -- if all 3
agree, skip reconcile.

---

## Self-Correction Protocol (arXiv:2606.05976 -- highest-ROI prompt change)

The Self-Correction Illusion: asking the model to critique its own last
assistant message in-place is largely ineffective. The model anchors to
its own prior output and fails to actually correct errors.

Role Relabeling Fix (+23 to +93pp explicit correction rate):

Never do this (in-place critique):
  Assistant: [erroneous answer]
  User: Please review and correct your answer above.

Do this instead (external hypothesis framing):
  [copy the suspect claim into a tool result or memory block]
  User: External hypothesis to verify: "<suspect claim>". Check this for errors.

Practical implementation:
  - Wrap suspect output in a <hypothesis> block or inject as a tool-result
  - For reasoning-chain errors: copy incorrect step into user content labeled
    "prior reasoning step -- verify this"
  - For tool output errors: put suspect output in a system/tool role block

Memory role wins on math; user role wins on logic.

---

## Context Dashboard (arXiv:2606.30005 VISTA; note: 22.7%->50.7% LOCA-Bench
is full VISTA on Gemini-Flash -- not reproduced by this lightweight approximation)

At the start of long-horizon L2/L3 tasks, inject into system prompt:

  --- Context Status ---
  Tokens used: {used} / {total} ({pct}%)
  Active blocks: {block_list}
  Archived: {archived_ids}
  Remaining: ~{remaining} tokens
  --- End Status ---

Update at key checkpoints. Do not hide budget from the model.

Context object classes -- different compression rules (arXiv:2608.31057):
  User instructions / acceptance criteria  -> PIN -- never compress
  Agent-generated plans                    -> KEEP until next verified checkpoint
  Tool output (large dumps)                -> ARCHIVE aggressively after one use
  Intermediate reasoning chains            -> COMPRESS after step is verified
  Error traces                             -> KEEP until error is resolved

---

## Memory-Augmented Reasoning (arXiv:2608.21265)

After completing a hard task (L2/L3), store a pattern card in Hindsight:

  Pattern: <task type>
  Constraints: <what made it hard>
  Critical operations: <key steps in order>
  Failure modes observed: <what went wrong / edge cases>
  Resolution: <what worked>

Tag with: ["reasoning-pattern", task_domain, difficulty_level]

At similar future tasks, hindsight_recall(query=task_type) and inject top
1-3 cards as prefill. Yields 1.14-1.49x latency speedup, +21-29pp accuracy vs Chain-of-Draft — not a Hermes target; do not treat those numbers as transferable.

---

## Adaptive Self-Consistency (arXiv:2601.02970, 2511.00751)

Key finding: blanket self-consistency with modern strong models yields only
+0.4% HotpotQA, +1.6% MATH-500 at k=20. Do NOT enable blanket SC.

Use adaptive SC only when:
  - Self-reported confidence is low
  - First answer fails a sanity check
  - Task is hard: AIME-class math, multi-hop reasoning, irreversible actions
  - Tool output contradicts expected result

Protocol (k=3):
  1. Get first answer. If confidence >= threshold -> STOP
  2. If low confidence -> get 2 more; reduce by frequency x stated confidence
  3. Max k=4. Do not scale past k=4 without a verifier.

Anthropic caches context prefix: k=3 costs ~1.5x (not 3x). See
hermes-swarm-consensus section "Prompt Caching Fast Path".

---

## Temporal Constraint Enforcement (arXiv:2512.23738, 77.4% -> 100% conformance)

For L3 tasks with ordered operations, list constraints before starting:

  Temporal constraints:
  1. Verify current state BEFORE any modification
  2. Dry-run BEFORE any irreversible action
  3. User confirmation BEFORE external communication or payment
  4. Checkpoint BEFORE database/file mutations

Before each tool call, verify it satisfies the constraints. Regenerate if violated.

---

## Planning and Tool-Use Protocols (from research batch, Sep 2026)

### Tool Necessity Gate — Invoke Only When Epistemically Needed
Before every tool call (especially web_search, execute_code, terminal),
verify the call is necessary:
  One line: "Need: [cannot answer from current context because X]."
If the answer is already in context, skip the call. This is especially
important for expensive tools (web_search, API calls, model delegation).
Do NOT call tools to confirm what you already know.

### Pre-Call Scoring (ToolTree pattern)
For expensive or side-effecting tools, run a quick pre-call gate:
  {"score": 0.0-1.0, "why": "...", "proceed": true/false}
Score > 0.7: proceed. Score < 0.4: reconsider or clarify first.
This applies especially to: file writes, terminal mutations, API calls,
model delegation, and any L3 irreversible action.

### No Mid-Trajectory Abort on Confidence Dip
Do NOT abort a running task because mid-task confidence dropped.
Confidence at intermediate steps is unreliable — tasks that look hard
mid-trajectory often resolve correctly at the end.
Abort rules:
  - Detected loop (same tool call 3× with same args): stop, report
  - Verifier explicitly failed 3× in a row: stop, escalate
  - User constraint was violated: stop immediately
Never abort just because a step returned unexpected data or "seemed hard."

### Conditional Repair — Only on Actual Failure
Repair prompts should be gated on real failures, not on routine steps:
  If last tool succeeded: do not reflect, do not repair, proceed.
  If last tool failed: identify the failure mode, attempt ONE repair.
  If repair also fails: escalate or report, do not loop indefinitely.
Max repair attempts per step: 2. After 2 failures, skip or escalate.

### Coarse-to-Fine Planning (AdaPlan-H / HiPlan)
For L2+ tasks: default to a 3-5 step coarse plan first. Expand a step
into substeps only if the next action requires it. Do not write a 20-step
plan upfront — most steps depend on prior results and will be wrong.
Emit milestones (not individual actions) for long-horizon tasks:
  Plan: [milestone-1, milestone-2, ..., milestone-N]
  Each turn: execute toward current milestone, advance on completion.

## Metacognition, Uncertainty, and Self-Correction

### Prefer "Unknown" Over Hallucination
If you cannot answer from context/tools/memory, say so directly:
  "I don't know this; I'll look it up" or "I can't verify this — here's
  what I do know vs what I'd need to confirm."
Do NOT fill epistemic gaps with plausible-sounding invented facts.
Confidence < 0.7 on a factual claim: flag it explicitly or retrieve.

### Constitutional Critique Checklist
For L3 tasks and any output that will be acted on without further review,
apply a short constitutional checklist before finalizing:
  1. Is every stated fact either from context/tool output, or flagged uncertain?
  2. Are irreversible actions verified (dryrun/read-back/test)?
  3. Does the output satisfy the original constraints as literally stated?
  4. Have I checked for off-by-one, sign, or unit errors in any numbers?
  5. Would a skeptical expert find a flaw here? If yes — fix it first.

### CRITIC: Tool-Grounded Critique (Not Unaided Self-Critique)
For factual or code claims, a critique step MUST include at least one
tool call to verify (re-read file, run test, search source). Pure
verbal self-critique that doesn't call tools has ~0pp improvement rate.
Pattern:
  1. State the claim to verify
  2. Call the verifying tool (read_file, terminal, web_search)
  3. Compare tool output to claim
  4. Correct if discrepancy found

### Cap Self-Refinement: max 2 loops, require new evidence
Do not enter more than 2 self-refinement loops on the same output.
Each loop MUST bring new evidence (tool result, test outcome, or role
relabeling) — not just verbal re-examination. Third time: stop,
deliver best current answer with explicit uncertainty annotation.
Config reference: adaptive_reasoning.self_correction.max_self_refine = 2

### Metacognitive Gates for Irreversible Actions
Before any L3 (irreversible/high-stakes) tool call:
  - State confidence level explicitly: "Confidence: X/10"
  - If confidence < 7/10: pause and clarify or gather more evidence first
  - Verify preconditions are met (files exist, env is correct, etc.)
  - For external actions (email, publish, deploy): re-read the full
    action spec one more time before executing
This is not optional for L3 — it is a mandatory step.

### AgentSpec Deny-by-Default for Irreversible
For unattended/autonomous runs, apply deny-by-default to:
  - Any file deletion or overwrite without a prior read
  - Any external publish/send/deploy without explicit prior confirmation
  - Any database mutation without a WHERE clause check
  - Any shell command with rm, DROP, truncate, or DELETE
In attended sessions: still apply pre-call gate before executing.

## Extracted paper protocols

Math/CS foundations, Cycle-1 metacognition (Typed Uncertainty, Abstention,
CONVOLVE stop-rules, SteerConf, Progress-Gated Routing, Final-Step JOL,
Claim Freshness, FOK/JOL harness, Skill Profile, CONFIRMED Early-Stop,
Compositional IU/EU), error-recovery, tool-use, token-budget, scratchpad
security, meta-reasoning, and structured-output protocols live in
`references/adaptive-reasoning-research.md`. Do not re-expand them here.

## Subsystem Wiring and Limitations

The scripts are opt-in skill-protocol tools NOT auto-enforced by Hermes runtime.
The config.yaml `reasoning_research:` block is documentation + policy defaults, NOT
automatically consumed by Hermes. Script behavior is controlled via MH_* env vars only
(the harness docstring says 'config.yaml or env' but only env is implemented).
The `adaptive_reasoning:` block in config.yaml is also documentation only.

Script env var reference (all scripts ignore config.yaml; set via env or .env):
  MH_JOL_STOP=0.8     jol_stop_threshold
  MH_GAP=0.3          fok_jol_gap_threshold
  MH_MAX_ATTEMPTS=2   max_attempts_before_list_wise
  MH_CONF_GATE=0.8    confidence_gate.confidence_threshold
  MH_DELEGATE=0.6     skill_profile.delegate_threshold
  MH_BLEND=0.5        skill_profile.blended_weight
  MH_MIN_SAMPLES=5    skill_profile.min_samples_before_delegating
  MH_DB=~/.hermes/memory-facts/metacognitive.db

  L3 -> trajectory-risk-guardrail: Load before any mutating call. L3 implies
    irreversible/high-stakes; the guardrail's verify-before-mutate applies.

  L3 -> claude-routing-hierarchy: Consider stronger model tier for L3 tasks.

  L2-L3 -> hermes-context-budgeting: Apply budget_tokens from classify output
    as the reasoning token limit for the task.

  Pattern-card write (Hindsight): After a successful L2+ trace:
    hindsight_retain(content='<trace summary>', tags=['reasoning-pattern'])
    Enables memory-augmented CoT injection (+21-29pp, arXiv:2608.21265).

  working-memory.py: Pass classify result to add-constraint:
    python3 ~/.hermes/scripts/working-memory.py add-constraint \
      --text "reasoning_level=L3" --binding must
    python3 ~/.hermes/scripts/working-memory.py add-constraint \
      --text "max_tokens=3000" --binding must
  (Note: --constraint is not a valid flag; use --text + --binding)

## Limitation: Homogeneous Swarm

Minority Sentinel's 25% minority-truth rate (arXiv:2606.29270) assumes
heterogeneous multi-vendor agents with stance_change fields. Live Hermes
uses mixed parent/delegate models (parent `claude-sonnet-4-6` / anthropic,
delegation `grok-4.6` / xai) but a given swarm is still homogeneous if all
workers share one model. Do not assume the 25% rate on a single-model swarm.

## Calibration Loop (Sep 2026 — do not confuse with Round 1 Calibration Loop above)

  # After each L2/L3 task:
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py calibrate \
    --task "<task>" --predicted L2 --actual L2 --correct 1

  # Monthly check:
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py stats
  # Accuracy < 0.75 after N entries -> review signal weights
 Under-reasoning rate > 0.25 -> weights for structure/depth signals too low
 Over-reasoning rate > 0.25 -> weights for trivial signals too high in the classifier

---

## Metacognitive Control Protocol (Sep 2026)

### Hard Confidence Gate (prompt-level implementation)
If confidence is high (verbalized >= 0.8) but no tool call or citation
has been made, FORCE a tool call or escalate — do NOT deliver the answer.
Verbal confidence alone without evidence is the primary Confident Failure mode.

### FOK/JOL: External Control vs In-Turn Proxy
arXiv:2605.14186 gains (48.3->56.9pp) used an EXTERNAL SVM controller fitted on held-out outcomes,
not an in-turn self-scoring loop. In-turn FOK/JOL scores are a prompt-level proxy only.
To use correctly: consume FOK/JOL via metacognitive-harness.py from a DIFFERENT turn/pass,
not in the same turn that also generates the answer.
Advisory only when used in-turn; external controller is the paper's measured setting.

Gap evaluation order: check |FOK-JOL| FIRST (before JOL-stop). FOK=0.2, JOL=0.9 is an
  overconfidence signal (gap > 0.3) -> RETRY, not stop.

## Planning Protocols (Sep 2026)

### Unified Planning Stack (one authoritative order; resolves all contradictions)
All planning guidance below follows this stack. When instructions conflict, this wins:
  1. Retrieve milestone library from Hindsight for similar past tasks (global orientation).
  2. Emit 3-5 coarse milestones. Expand ONLY the current milestone into steps (lazy expansion).
     Expand at most 3 steps per milestone (N/3 horizon; 2608.06663). Checkpoint after each 3 steps.
  3. On each material observation: rewrite REMAINING subgoals only (not past milestones).
  4. Commit to a verified answer/action BEFORE stopping. Do not stop before VERIFY step.
  5. Put control flow in code (seq/branch/retry nodes), not in a monolithic prompt.
  6. Plan over skill names (search/code/write/delegate), not raw tool names.
  7. Fan-out (parallel workers) only when: (a) IB relay-sufficiency passes AND
     (b) subtasks/hypotheses are genuinely independent (no data dependency).
Note: commit-and-stop (step 4) does NOT skip VERIFY. Stop AFTER verify, not before.
Note: 2604.00130 +6.2%/2605.11746 58%-confabulation/2608.24658 1.7x are benchmark figures;
  transfer to prompt-only Hermes tool loops is unconfirmed.

## Safety Protocols (Sep 2026)

### AgentSpec Advisory Rules (prompt-level reminders)
For irreversible or high-risk tool calls, apply a pre-call monitor:
  Pattern (Python-expressible):
    if trigger(tool_name, args):
        if not predicate(args, context):
            block_and_reprompt("Constraint violated: {reason}")
Example rules:
  - rm/DELETE with no prior read of target -> block
  - HTTP POST/PUT without reviewing request body -> reprompt
  - external send (email/publish) without prior user confirmation -> block
  - any DROP/TRUNCATE/WIPE without explicit confirmation flag -> block
Draft rules with LLM, then human-filter for precision before enabling enforce mode.

**Dynamical Loop Regime Detection (arXiv:2512.10350 Geometric Dynamics; arXiv:2606.18206 Fixed-Point Reasoners)**
Recursive agent loops exhibit 3 regimes: contractive (convergent, stable), oscillatory (cycling, stuck), exploratory (widening search space).
Spike K filed: detect regime via embedding distance between iteration outputs.
  cosine_dist(embed[N], embed[N-1]) < 0.05 for 3 rounds -> contractive -> early-stop
  cosine_dist oscillates > 0.15 for 5 rounds -> oscillatory -> escalate or force synthesis
  cosine_dist > 0.3 sustained -> exploratory -> allow continuation
Current working-memory.py uses fixed iteration count. Regime detection is a new stopping criterion.
Feasibility gate: verify embedding API latency is acceptable before enabling.

**Embodied Relevance Realization Ceiling (Frontiers Psych 2024)**
Pure information-theoretic relevance realization has a ceiling: true relevance requires
embodied agency that self-organizes its relevance landscape via environmental coupling.
For Hermes: tool feedback (not just context scoring) is the load-bearing relevance signal.
IMPLICATION: do not rely solely on salience scores for what matters; tool outcome feedback
(tool failed / succeeded / returned unexpected) is first-class relevance evidence.
Already partially implemented: causal-check and abductive hypothesize both fire on tool
failure. Strengthen by treating tool-outcome surprises as relevance landscape updates.

**FOK/JOL Calibration Requirement (arXiv:2605.14186)**
FOK/JOL gates must be calibrated against historical outcomes to be meaningful.
Paper shows external SVM controller fitted on held-out outcomes achieves 48.3->56.9pp.
In-turn verbal FOK/JOL is advisory proxy only (already noted in Metacognitive Control
Protocol section). NEW: add calibration logging to track per-class FOK accuracy.
Spike M filed: calibration_log.jsonl records (session_id, task_class, fok_pred, outcome).
Weekly batch: compute per-class FOK accuracy; adjust I-CALM threshold per class if
hit_rate < 0.6 for that class.
Config addition (pending adversarial review): metacognition.fok_calibration_window_days: 30

## Novel Metacognition Techniques — Cycle 2 (Sep 2026 Research Sweep)

### Confidence Score Routing Table (which score for which decision)
Use the right confidence signal for each decision type. Never mix them.

  FOK (pre-task)            : Can I solve this? -> gates whether to attempt or escalate
  JOL (post-attempt)        : Am I satisfied with this answer? -> stop/retry/list-wise
  trajectory_confidence     : Multi-step rollup -> mid-trajectory REPLAN (not abort)
  retrieval_confidence      : Did search find relevant evidence? -> search-more or synthesize
  reasoning_confidence      : Is synthesis correct? -> flag UNCERTAIN or deliver
  U_tool                    : Right tool for this step? (>0.4 -> try different approach)
  U / IU / EU               : Compositional step uncertainty (>0.4 before write/send -> clarify)
  source_reliability        : Trust of stored belief (< 0.5 -> UNCERTAIN tag)
  freshness                 : Age-relative to half-life (< 0.5 -> STALE, re-fetch)
  pre-call score            : Worth calling this tool? (>0.7 proceed, <0.4 reconsider)
  Hard gate threshold       : 0.8 for irreversible actions (abstain-check script)
  I-CALM payoff threshold   : 0.7 for L2/L3 ambiguous (choose ABSTAIN/ASK vs ANSWER)
  ProgRouter threshold      : 0.7 for mid-trajectory re-routing escalation

Note: thresholds are policy defaults. Calibrate on outcomes if data is available.

### MED-Priority Techniques (informative, not prescriptive)

**Predict-Then-Answer (arXiv:2606.32032 RL-Metacognitive-Feedback)**
RL training with predict-before-answer ordering elicits better calibration than prompt-only.
Prompt approximation: for L3 tasks, structure the response as:
  1. Predict accuracy: "I estimate P(correct) = X because [reason]"
  2. Then answer
This is weaker than the RL setting but reinforces calibrated self-assessment before commitment.

**Automata Stop Patterns from Traces (arXiv:2608.23670)**
Pattern-matching against prior session traces predicts failure 3 steps ahead (71% accuracy).
Extends CONVOLVE stop-rule mining (`references/adaptive-reasoning-research.md`,
arXiv:2606.28733). After that mining:
  Also mine: recurring N-step state-transition patterns that preceded failure
  Store in Hindsight with tag ["failure-automaton", task_type]
  At matching situations: check against before proceeding

**Belief Anchoring vs Contradiction Acceptance (arXiv:2603.23848 BeliefShift)**
Without belief anchoring, models accept contradictory updates 67% of the time.
With explicit belief tracking + version stamps: 23%. Extends Graphiti valid_until rule:
  When a new piece of information contradicts a prior stored belief:
  1. Flag the contradiction explicitly: "BELIEF UPDATE: prior=[X] new=[Y] — they conflict"
  2. Investigate which is more recent/reliable before updating
  3. Do not silently overwrite; preserve the prior with a superseded marker

**Mechanistic CoT Faithfulness (arXiv:2602.11201)**
CoT steps after commitment are mechanistically post-hoc (attention bypasses them).
This provides mechanistic grounding for the commit-and-stop rule (2605.11746).
No new protocol needed; strengthens the existing commit-and-stop rule:
  Reasoning after a committed answer is not additional evidence; it is confabulation.
  Stop sooner.

## Bias-Variance Decomposition for Agent Calibration (Hastie ESL Ch 7)

**Theory:** Prediction error decomposes into bias² + variance + irreducible noise. High variance = model too sensitive (inconsistent across runs). High bias = model systematically wrong direction.

**Hermes rules:**
- **High-variance agent** (outputs differ substantially across runs on the same task): lower temperature, use self-consistency (k=3), or add structural constraints to the prompt. Variance is the problem, not model capability.
- **High-bias agent** (consistently wrong in the same direction — e.g. always underestimates scope, always omits security considerations): switch model tier or expand the context with domain-specific examples. Sampling more from the same model does not fix bias.
- Diagnose before treating: run the same task 3 times (or review 3 prior runs). High spread = variance; consistent miss = bias. Different interventions apply.

**Citation:** Hastie, Tibshirani, Friedman — *Elements of Statistical Learning* (2nd ed.), Ch 7 (Model Assessment and Selection — bias-variance decomposition).

## Pitfalls

- Do not use max-token reasoning on all tasks. Over-reasoning on simple lookups
  reduces accuracy. (arXiv:2608.20256 shows ~41% token reduction on GRPO-trained
  1.5B models -- that number does not directly transfer to prompt-based agents,
  but the over-reasoning failure mode is real.)
- Do not critique your own last assistant message in-place. Role relabeling
  gives +23-93pp (arXiv:2606.05976).
- Do not use naive majority vote for BRANCH reduction. Use DCR or list-wise
  judge (arXiv:2608.15303).
- Do not run homogeneous self-consistency panels. Verbalized sampling prefix
  breaks mode-collapse (hermes-swarm-consensus).
- Do not treat token count as the primary quality metric. Track task success
  rate and correctness alongside spend.
- Do not skip L3 classification because a task "looks short". Irreversible
  actions are L3 regardless of word count.

## Extended Reasoning Frameworks (Sep 2026)

Wire-up for causal, action-boundary, lookahead, and abductive checks.
Scripts are opt-in (same as the rest of the metacognitive harness): config keys
are policy defaults, not runtime. Invoke the commands below at the listed gates.

### Causal Reasoning Check

When to use: before attributing cause to any observation; when debugging or explaining failures.

  python3 ~/.hermes/scripts/metacognitive-harness.py causal-check \
    --observation "X" --candidate-cause "Y"

Config keys: `reasoning_research.reasoning_frameworks.causal_reasoning.*`
Research: Pearl counterfactual test; arXiv:2502.09100 (logical reasoning in LLMs)
Exit codes: 0=causal_confirmed, 1=correlation_only, 2=unknown

### Action Boundary Check (EBP)

When to use: before claiming task complete; before verify-gate; when task has multiple sub-steps.

  python3 ~/.hermes/scripts/metacognitive-harness.py boundary-check \
    --action "X" --task "Y"

Config keys: `reasoning_research.reasoning_frameworks.action_boundary.*`
Research: ACL 2026 "Action Boundary Blindness" (EBP; ABS +0.08-0.13, +9.2% SR, cited as design target).
  Also arXiv:2607.10059 AgentAbstain — abstain must be pre-execution, not post-hoc.
Exit codes: 0=clean, 1=incomplete, 2=over_action, 3=scope_creep
Integration: call before working-memory verify-gate for L2+ tasks. Complementary to abstain-check (confidence) — do not skip either.

### Future-Aware Planning (Lookahead)

When to use: before irreversible actions; when planning horizon > 5 steps; on L2+ tasks.

  python3 ~/.hermes/scripts/working-memory.py lookahead --session SID --action "X"
  python3 ~/.hermes/scripts/working-memory.py subplan-verify --session SID --subplan '[...]'

Config keys: `reasoning_research.reasoning_frameworks.future_aware_planning.*`
Research: arXiv:2601.22311 (FLARE) — reasoning != planning; step-wise greedy fails long-horizon
Research: arXiv:2604.11978 (HORIZON) — non-linear collapse above horizon threshold
Exit codes lookahead: 0=proceed, 1=caution, 2=block

### Abductive Hypothesis Generation

When to use: when a tool fails unexpectedly; when a retry loop forms; when cause is unclear.

  python3 ~/.hermes/scripts/critique-bank.py hypothesize \
    --observation "X" --context "Y"

Config keys: `reasoning_research.reasoning_frameworks.abductive_reasoning.*`
Research: Peirce abduction; arXiv:2505.21935 (hypothesis discovery with LLMs)
Exit codes: 0=hypotheses_generated

See references/adaptive-reasoning-research.md for arXiv paper survey.
