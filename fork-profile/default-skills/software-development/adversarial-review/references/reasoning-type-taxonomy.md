# Reasoning Type Taxonomy and Hermes Gap Map

Source: Sep 2026 research sweep (arXiv:2502.09100, arXiv:2607.05775, arXiv:2601.22311,
arXiv:2604.11978, ACL 2026 Action Boundary paper, Peirce abduction, Pearl causality).

This file lives in adversarial-review/references because the gap analysis is a prerequisite
for adversarial review of any agent reasoning implementation. For the primary workflow, see
adaptive-agent-reasoning (run `hermes curator adopt adaptive-agent-reasoning` to make
it curator-managed and add this as a linked reference there).

## Canonical Taxonomy (9 types)

FORMAL / LOGICAL
  Deductive    — general premises → certain conclusions; theorem proving, entailment
  Inductive    — observations → probabilistic generalizations; pattern learning
  Abductive    — best explanation for incomplete observations; hypothesis generation

RELATIONAL / CAUSAL
  Causal       — cause-effect chains, counterfactual intervention; Pearl do-calculus
  Relational   — structural connections between objects; graph/spatial relationships
  Analogical   — structure-mapping from source domain to target domain

CONTEXTUAL
  Common-sense — default world knowledge, pragmatics, implicit context
  Social       — theory of mind, cooperation, stakeholder goals, multi-party intent
  Ethical      — deontic/permissibility reasoning, value alignment, moral tradeoffs

PLANNING-SPECIFIC (distinct from reasoning)
  Future-aware — explicit lookahead, backward value propagation, receding-horizon replanning
  CRITICAL: CoT/ReAct are step-wise greedy reasoning policies, NOT planning.
  Conflating them is a documented failure mode (FLARE, arXiv:2601.22311).

## Hermes Gap Inventory (Sep 2026)

GAP 1 — CAUSAL REASONING (HIGH)
  No native causal primitive. Agents conflate correlation with causation.
  Pearl counterfactual test: "Would outcome change if cause were absent?"
  Confound patterns: temporal proximity alone, shared-driver confound, selection bias.
  Implementation target: metacognitive-harness.py causal-check subcommand.
  Config key: reasoning_research.reasoning_frameworks.causal_reasoning

GAP 2 — FUTURE-AWARE PLANNING vs STEP-WISE REASONING (HIGH)
  arXiv:2601.22311 (FLARE): CoT, ReAct, beam search are greedy step-wise policies.
  They systematically fail long-horizon tasks regardless of model scale.
  Three requirements for coherent planning:
    1. Explicit lookahead (counterfactual future state evaluation)
    2. Backward value propagation (terminal outcomes inform early decisions)
    3. Limited commitment / receding-horizon replanning
  arXiv:2604.11978 (HORIZON): non-linear performance collapse above horizon threshold.
  Implementation target: working-memory.py lookahead + subplan-verify subcommands.
  Config key: reasoning_research.reasoning_frameworks.future_aware_planning

GAP 3 — ABDUCTIVE REASONING (MEDIUM)
  Best-explanation inference; crucial for debugging and anomaly detection.
  arXiv:2505.21935: full abduction-deduction-induction cycle for hypothesis discovery.
  Implementation target: critique-bank.py hypothesize + false_attribution failure mode.
  Config key: reasoning_research.reasoning_frameworks.abductive_reasoning

GAP 4 — ACTION BOUNDARY BLINDNESS (MEDIUM-HIGH, low effort)
  ACL 2026: best models ABS=0.424. Under-action dominates (48.4% of violations).
  EBP (Explicit Boundary Prompting): +0.08-0.13 ABS, +9.2% SR at near-zero cost.
  Implementation target: metacognitive-harness.py boundary-check subcommand.
  Trigger point: before verify-gate or completion claim at L2+.
  Config key: reasoning_research.reasoning_frameworks.action_boundary

GAP 5 — SOCIAL / THEORY-OF-MIND REASONING (MEDIUM, not yet implemented)
  arXiv:2602.02760 (WildGrid): agents fail objective inference under partial observability.
  Placeholder: reasoning_research.reasoning_frameworks.social_reasoning (enabled: false)

GAP 6 — ETHICAL / DEONTIC REASONING (MEDIUM, not yet implemented)
  Hawaii SLR: ethical reasoning absent from essentially all LLM agent research.
  Placeholder: reasoning_research.reasoning_frameworks.ethical_reasoning (enabled: false)

GAP 7 — ANALOGICAL REASONING (LOW)
  Skill routing is keyword/BM25, not structural analogy. Low priority.

GAP 8 — INDUCTIVE GENERALIZATION FROM FAILURES (LOW-MEDIUM)
  critique-bank.py captures failures but no cross-session inductive elevation.
  skillopt_score.py + gepa_skill_eval.py exist but don't feed back in-session.

## Adversarial Attack Vectors for Reasoning Implementation Review

When reviewing any implementation of the above frameworks:

1. PROJECTED-STATE CHECK: Functions that compute a future state then check constraints
   must use the PROJECTED state in the check, not the original.
   Pattern: grep for `new_state = f(old_state, ...)` and confirm downstream checks
   use `new_state`, not `old_state`. (See adversarial-review projected-state pitfall.)

2. POST-REVISION ACTION CHECK: When a gate calls revise() on a rejected action, confirm
   that the downstream execute/commit uses the REVISED action, not the original.
   (See adversarial-review post-revision pitfall.)

3. EXIT-CODE CONTRACT: Each subcommand must return a documented integer exit code.
   Verify cmd_* functions end with `return <int>` not just `print()` with implicit 0.

4. ARGPARSE CONSISTENCY: New subcommands must follow identical argparse + JSON stdout
   pattern as existing subcommands. Inconsistency breaks callers expecting uniform output.

5. DOCSTRING CURRENCY: After adding subcommands, verify the script's module docstring
   Usage: section lists ALL subcommands. Stale docstrings mislead future callers.

6. CONFIG-SCRIPT PARITY: Every config key added under reasoning_research.reasoning_frameworks
   must be documented in adaptive-agent-reasoning SKILL.md Config Key Reference table.
   Orphaned config keys with no skill reference are silently ignored.

7. ARGPARSE REQUIRED-VS-DEFAULT: Arguments that are semantically mandatory must use
   `required=True`, never `default=<plausible_string>`. A default like `default="framework-a"`
   silently accepts calls that omit the argument, producing output with a dummy placeholder
   as the framework name — misleading and undetectable at call sites. Check pattern:
   grep all `add_argument` calls for mandatory parameters that carry a `default=` instead of
   `required=True`. Fix: remove default, add required=True, update all call sites and skill
   examples. Also update module docstring Usage: section to show the argument as required.

8. MULTI-LINE CODE BLOCK REGEX CHECK: When auditing skill files for correct CLI invocation
   patterns (e.g. checking that `--framework-a` appears in every conflict-resolve call),
   single-line regex matches fail silently on backslash-continued multi-line commands —
   `python3 ... conflict-resolve \\` on line N with `--framework-a ...` on line N+1 will
   not match a per-line regex. Fix: extract code blocks between ``` fences first, join
   the block into a single string (stripping backslash-newlines), then apply the pattern.
   A regex that finds zero violations is only trustworthy if it was tested against a
   known-bad example before running on the real corpus.

9. DUPLICATE YAML BLOCK COHERENCE: When config keys appear at two YAML paths (e.g.
   `reasoning_research.reasoning_frameworks.reasoning_selection` AND a top-level
   `reasoning_selection` block written by a later agent), checks that read from one path
   will PASS while checks that read from the other will FAIL — without any visible error.
   Audit pattern: after any config write pass, parse the full YAML and enumerate all
   top-level keys; flag any key that duplicates a nested path. Remove the duplicate
   (the canonical nested path is always authoritative); add `both_unknown_action` and
   other missing fields to the canonical path, not a parallel block.

## Reasoning Failure Taxonomy (arXiv:2607.05775, 27 papers, 19 benchmarks)

6 failure clusters:
  1. Tool invocation + parameter-level errors
  2. Planning + constraint-satisfaction failures
  3. Long-horizon degradation from context accumulation
  4. Multi-agent coordination failures
  5. Safety + adversarial + underspecified conditions
  6. Measurement validity problems

Key finding: failures compound nonlinearly with task length.
Strong sub-task performance does NOT equal end-to-end success.
Scaffolding does NOT consistently improve reliability.

## Quick Routing Table for Reasoning Framework Selection

  Debugging / root-cause attribution   → causal-check (do not assume correlation = cause)
  Task completion / verify-gate claim  → boundary-check (completeness + scope)
  Long horizon / irreversible action   → lookahead (commitment level + recovery options)
  Retry loop / unexpected failure      → hypothesize (best-explanation candidates)
  Multi-step chain > 5 steps           → subplan-verify (pre-execution constraint check)
