---
name: ralph-loops
description: >
  Use when running an iterative autonomous loop where each pass starts with a fresh context, the spec/goal is reinjected clean each time, and the filesystem/git hold state. Beats multi-agent orchestration for repetitive improvement tasks because it avoids context rot, premature exit, and single-pass fragility.
version: 1.1.0
triggers:
  - "implement tickets from a backlog automatically"
  - "raise test coverage to X%"
  - "run until CI is green"
  - "loop until tests pass"
  - "self-improving skill / skill evolves after each run"
  - "iterate on this until it works"
  - "ralph loop"
related_skills:
  - autonomous-agent-loop-design
  - subagent-driven-development
  - test-driven-development
  - trajectory-risk-guardrail
  - mnemosyne-atp-safety
  - preact-trajectory-compilation
---

# Ralph Loops

Pattern coined by Geoffrey Huntley (named after Ralph Wiggum). The agent tries the same
goal repeatedly with fresh context each pass, using filesystem + git as memory.

## Why Ralph Loops Beat Multi-Agent Orchestration

Three failure modes Ralph loops fix:

1. **Context rot** — in long conversations, the context window accumulates every failed
   attempt until the original specification falls out. The model slides into a "dumb zone"
   of hallucination. Ralph loops wipe context each iteration; only the spec and filesystem state return.

2. **Premature exit** — agents declare victory too early (Anthropic research: "agents usually
   look around, see progress, and declare the job done"). Standard ReAct inherits this flaw.
   Ralph loops use *objective verification* as the only exit: tests pass, CI is green, coverage
   exceeds threshold. Not model self-assessment.

3. **Single-pass fragility** — one prompt, one context, one shot: when it fails, the failure
   is chaotic. Ralph loops make failure predictable and auto-correcting.

## How It Works

```
while <objective not met>:
    fresh_context() + spec + current filesystem state
    agent works toward objective
    objective_check()  # run tests / linter / CI / coverage
    if check passes: exit
    else: loop again, agent reads its own git diff from last attempt
```

State lives on disk (files + git). Each iteration:
- Starts with full spec (not a compressed summary)
- Reads the filesystem (including previous attempt's output)
- Can `git diff` to see what the last pass changed

## Three Implementation Modes (from simplest to most controlled)

### Mode 1 — bash while loop (most primitive)
```bash
while true; do
  claude "implement the next most important ticket from doc/tickets using TDD.
           commit when done. if all tickets are done, exit with 'DONE'."
done
```

Stop condition: intercept model output for your exit sentinel, or set a max-iterations wrapper.

### Mode 2 — Claude Code /loop command
```
/loop every 1 minute
build the next ticket from doc/tickets using TDD, run tests, commit when done.
```

Claude Code's built-in scheduler. Clean, retains session between iterations (shared context
mode). Use this when you want the model to explicitly review its own previous output.

### Mode 3 — Claude Code stop hook (most robust)
Wire an objective signal (test exit code, coverage %, lint count) to a stop hook.
The hook returns a non-zero exit to the agent if the goal is not yet met, preventing
the agent from stopping until the objective is satisfied.

```python
# Example stop hook pseudocode
def stop_hook(agent_output):
    coverage = run_coverage()
    if coverage < 95:
        return {"continue": True, "reason": f"Coverage is {coverage}%, need 95%"}
    return {"continue": False}
```

Boris Cherny (creator of Claude Code): giving Claude a way to verify its own work
increases quality 2-3x.

## Three Concrete Use Cases

### 1. Ticket backlog (TDD)
Set up `doc/tickets/` with numbered files (001, 002, 003…). Each describes a feature or fix.

```bash
while true; do
  claude "implement the next most important ticket from doc/tickets using TDD.
          run tests. mark done. commit. if all tickets complete, exit."
done
```

No dependency graph needed — the model reads all tickets, skips done ones, picks next priority.

### 2. Coverage ramp
```bash
while true; do
  claude "analyze coverage gaps, write tests for uncovered functions, run the suite,
          fix failures. stop only when coverage exceeds 95%."
done
```

Coverage report is the objective backpressure. Loop does not stop until numbers validate.

### 3. Framework / dependency migrations
React v16→v19, Next.js 14→15, Jest→Vitest. Clean exit condition: build passes, tests pass.

```bash
while true; do
  claude "migrate the project from Jest to Vitest. run build and tests. fix all errors.
          stop when both build and test suite are clean."
done
```

Compiler errors and failing tests act as the feedback signal.

## Self-Improving Skills (advanced)

The most powerful Ralph loop variant: at the end of each run, the skill *updates itself*
with what it should have done differently.

**STAGING-FIRST pattern (required for autonomous / cron runs):**

Instead of applying skill patches directly in-loop, stage them to
`~/.hermes/cache/pending-improvements/` and let the curator (slow pass, 168h) review and apply:

```bash
while true; do
  claude "run /my-skill. when done, identify any improvements to the skill.
          Write the proposed patch as markdown to:
            ~/.hermes/scripts/stage-improvement.sh <skill-name> '<one-liner>'
          Then pipe the proposal body to stdin of that script.
          Do NOT call skill_manage directly. Stage only."
done
```

For interactive sessions where the user is present, direct `skill_manage` patching remains fine.
Staging is required only when the loop is autonomous (cron, ralph-loops, subagent chains).

This creates a self-improving mechanism with a review gate:
- Fast loop discovers improvements (low cost, high throughput)
- Slow curator applies them (safety, deduplication, adversarial check)
- Quality improves without compounding fast-loop noise into skills

**Staged proposals live in:** `~/.hermes/cache/pending-improvements/*.md`
**Review them with:** `ls -lt ~/.hermes/cache/pending-improvements/`
**Apply a staged patch:** read the file, then call `skill_manage(action='patch', ...)` manually.

**REQUIRED: Gate all self-improvement steps with the staging path.** (See safety section.)

## Safety Rules

**NEVER run Ralph loops with irreversible side effects outside the repo.**

Real incident: a Claude Code agent ran `terraform destroy` on DataTalks.Club's production
infrastructure — wiped the database, VPC, and all automated snapshots. 2.5 years of data gone.
The loop had no exit condition that checked the scope of what it was destroying.

Rules:
- Ralph loops are safe when **repo-contained** and the **toolchain acts as judge** (tests, linter, CI).
- Add `--allowedTools` or tool restrictions to prevent filesystem access outside the project.
- If the loop *can* destroy shared state, require manual review of every plan before execution.
- Use a maximum iteration count (e.g., `MAX_ITER=20`) as a safety backstop.
- Review every loop that touches databases, infrastructure, secrets, or external APIs.

## Stopping Conditions (use ALL that apply)

| Task | Stop when |
|---|---|
| TDD backlog | all tickets marked done AND tests green |
| Coverage ramp | coverage >= threshold AND tests green |
| Migration | build passes AND full test suite passes |
| Self-improving skill | human reviews and approves the proposed changes |
| CI fix loop | CI pipeline green |

**Never** stop on model self-assessment ("I think it's done"). Always stop on an
objective, executable signal.

### Span Seminorm Stopping Criterion

Span seminorm stopping criterion (Puterman Ch 6): in any rescoring or belief-updating loop with 3 or more iterations, prefer sp(v) equal to max(v) minus min(v) below 0.02 as the stopping criterion over a fixed iteration cap or nothing-changed check. This is tighter than norm-based stopping and avoids oscillation cycles. For score vectors in [0,1], epsilon=0.02 gives practical convergence in 5-8 iterations. See also: puterman-mdp skill, agent-runtime-loop-patterns.

### Lyapunov Runaway Heuristic

Lyapunov runaway heuristic (Astrom-Murray Ch 4): define V_n as distinct_tool_types_used_in_last_5_turns divided by total_tool_calls_in_last_5_turns. If V_n is non-increasing for 3 or more consecutive 5-turn windows AND total_turns is above 10 AND V_n is below 0.20, flag as tool-diversity collapse (likely limit cycle). Action: halt the loop and force a new tool branch or escalate to user.

## Integration with Hermes

Before starting a Ralph loop, run select-frameworks to determine which reasoning gates apply each iteration:
  ```
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<loop goal>" --level <L>
  ```
  L0-L1: exit 1 + `"proceed": true` — no gates; do not treat as failure.
  L2-L3: run lookahead before side-effecting iterations, subplan-verify before each phase boundary.

For long-horizon loops, run lookahead before each iteration with side effects:
  ```
  python3 ~/.hermes/scripts/working-memory.py lookahead \
    --task "<loop goal>" --next-action "<this iteration action>" --steps-remaining <n>
  ```
  Exit 1 (MEDIUM risk, HIGH commitment): confirm recovery path before proceeding.
  Exit 2 (HIGH risk): pause loop. Attended: escalate. Unattended: fail-closed skip
  this iteration (`HERMES_UNATTENDED=1`); do not wait for a human.

If conflict-resolve returns exit 2 (both UNKNOWN) inside a Ralph/cron loop: skip
the contested action, log, continue or abort the loop — never invent a verdict.

In Hermes, Ralph loops map to:
- **Cron jobs** (`/cron`) for scheduled iteration
- **`autonomous-agent-loop-design`** for numeric objective + cheap surrogate discipline
- **`self-improve-agent`** for the skill-evolution variant
- `while true; do claude "..."; done` in a background terminal process

Set a budget cap (`--max-budget-usd`) before any multi-iteration run.

## Theory-Grounded Loop Discipline

### AdaBoost Weighting for Iterative Refinement (Hastie ESL Ch 10)

**Theory:** AdaBoost assigns exponentially higher weight to misclassified examples on each boosting round — harder instances get more attention, not uniform treatment.

**Hermes rule:** In iterative ralph refinement, weight harder sub-tasks more each pass:
- If sub-task i failed in pass t, increase its attention weight by exp(α_t) where α_t is proportional to the failure severity (e.g. number of failing tests).
- On the next pass, prioritize those sub-tasks first — do not treat all sub-tasks uniformly after failure.
- Do NOT cycle through a fixed agenda regardless of per-item outcome.

**Citation:** Hastie, Tibshirani, Friedman — *Elements of Statistical Learning* (2nd ed.), Ch 10 (Boosting and Additive Trees).

### LTL Liveness as Loop Exit Criterion (Huth-Ryan Ch 3)

**Theory:** In Linear Temporal Logic, the formula GF(φ) means "globally, eventually φ holds" — i.e. φ must occur infinitely often. For agent loops, the progress liveness property is GF(progress): every finite prefix of the loop must be followed by measurable progress.

**Hermes rule:** If no measurable progress is made in the last N iterations (N ≥ 3), the liveness property GF(progress) is violated — terminate the loop. Liveness violation is the formal justification for the loop exit rule; self-assessment ("I think it's close") does not satisfy GF(progress).

**Citation:** Huth & Ryan — *Logic in Computer Science* (2nd ed.), Ch 3 (Linear Temporal Logic).

### Modified Policy Iteration m-Step Lookahead (Puterman Ch 6)

**Theory:** Modified policy iteration uses m backup steps before policy improvement: m=0 recovers value iteration (greedy), m=∞ recovers full policy evaluation (expensive). For finite-horizon agent loops, m=3 balances cost and quality.

**Hermes rule:** Before a REPLAN decision, evaluate m=3 steps ahead (project 3 candidate loop iterations and their likely outcomes) rather than either greedy one-step lookahead or full policy evaluation over all remaining iterations. This is the correct decision depth for moderate-horizon loops (5–20 remaining iterations).

**Citation:** Puterman — *Markov Decision Processes*, Ch 6 (Modified Policy Iteration).

## Feedback Token Cap (AgentLoopMiddleware pattern, 2026-08)

<!-- why: prevents context rot from runaway feedback accumulation across iterations -->

Each loop iteration that records "what went wrong" can balloon. Cap the feedback
accumulation explicitly to prevent the feedback log from consuming the context budget
meant for the actual work:

```python
MAX_FEEDBACK_TOKENS = 140  # ~1-2 sentences max per iteration

def record_feedback(iteration_log_path, text):
    """Append iteration feedback. Hard-cap at MAX_FEEDBACK_TOKENS."""
    words = text.split()
    if len(words) > MAX_FEEDBACK_TOKENS:
        text = " ".join(words[:MAX_FEEDBACK_TOKENS]) + " [truncated]"
    with open(iteration_log_path, "a") as f:
        f.write(f"\n--- iter {datetime.now().isoformat()[:16]} ---\n{text}\n")
```

Also implement `should_continue(iteration_n, objective_met)` as an explicit callback
before re-entering the loop body — separate from the objective check:

```python
def should_continue(iteration_n, max_iter, objective_met):
    if objective_met:
        return False, "objective met"
    if iteration_n >= max_iter:
        return False, f"iteration cap {max_iter} reached"
    return True, None
```

Never let the loop decide to continue based on model self-assessment alone.
`should_continue` must be called before every re-entry — it's the mandatory gate.

## Aug 2026: Initializer+Coder Two-Agent Harness (Anthropic Engineering Blog)

Source: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
Anthropic's production pattern for long-running agentic coding loops:

**Initializer agent** writes before the loop starts:
- `claude-progress.txt` — plain text, current state summary
- `feature_list.json` — JSON array of features with `{name, description, passes: false}` default
  (JSON not Markdown — models less likely to corrupt structured data)
- `init.sh` — baseline verification script

**Coding agent** at each loop iteration:
1. Read `claude-progress.txt` + `git log --oneline -10` to orient
2. Run `init.sh` to verify baseline still passes
3. Work ONE feature at a time — mark complete ONLY after end-to-end testing
4. Git commit with descriptive message at end of each feature
5. Set `passes: true` in feature_list.json ONLY after commit

**Failure modes and solutions (Anthropic empirical):**
1. Premature completion declaration → require git commit before marking done
2. Half-implemented features at context boundary → JSON checklist, not prose tracking
3. Not testing end-to-end → mandatory `init.sh` run at start of each iteration
4. Runaway context consumption → one-feature-at-a-time constraint, git commit as checkpoint

**Ralph-loops adaptation:** use this structure for ralph iterations involving code. The
feature_list.json becomes the ralph iteration log, git commit is the atomic iteration boundary.

## Semantic Early-Stopping for Text-Refinement Sub-loops (arXiv:2606.27009)

For writer-critic, summarization, and refinement sub-loops *within* a ralph iteration:
halt when output stops changing meaningfully rather than running a fixed iteration count.

```python
def should_halt_early(outputs: list[str], threshold: float = 0.02, patience: int = 3) -> bool:
    """Halt if cosine distance between consecutive outputs < threshold for `patience` steps.
    Requires: sentence-transformers or any embedding API. No model internals needed.
    Scope: homogeneous text loops ONLY (draft→refine, summarize→compress, etc.).
    Do NOT apply to heterogeneous tool-call sequences — tool output types change each step."""
    if len(outputs) < patience + 1:
        return False
    from numpy.linalg import norm
    import numpy as np
    def cos(a, b):
        a, b = np.array(a), np.array(b)
        return np.dot(a, b) / (norm(a) * norm(b) + 1e-9)
    # Use local embed call (hindsight embed or sentence-transformers)
    # deltas = [1 - cos(embed(outputs[-i-1]), embed(outputs[-i])) for i in range(1, patience+1)]
    # return all(d < threshold for d in deltas)
    return False  # replace with real embed call
```

Empirical result: judge-free cosine-plateau halting cut tokens 38% at quality parity.
Threshold 0.02 is a starting point — calibrate per task type after 20+ runs.
Do NOT claim Lyapunov contraction formally; treat as attractor detection heuristic.

## SEU Filter Between Iterations (PATH-Bench, arXiv:2608.01149)

After each iteration, before passing context to the next:
1. Is the next task the same domain as the previous? If yes: carry full context forward.
2. If different domain: strip task-specific artifacts (tool outputs, intermediate steps) from context before re-injection.
3. This prevents earlier iterations polluting later ones with irrelevant procedural detail.

## Control-Theory Loop Stability (cross-reference)

For Lyapunov-based runaway detection (3-step non-convergence halt), integral windup retry caps, and feedforward vs feedback dispatch selection, load: astrom-murray-feedback. For limit-cycle detection via state-hash (same output hash within 6 iterations = halt) and bifurcation-safe config tuning (max 10% per step), load: strogatz-dynamical-systems. These skills contain the authoritative rules; do not duplicate them here.

## Goal-Constraint Discipline (Five Focusing Steps for agent loops)

At any moment, identify the most binding constraint on goal progress — the element that, if unblocked, would most accelerate observed completions. When multiple blockers exist, pick the one that gates the most pending work.

| concept | loop equivalent |
|---|---|
| the goal | observed, evidence-backed completion — never artifact count, busy-ness, or self-assessment |
| throughput | rate at which required criteria become satisfied with evidence refs |
| inventory | everything prepared_not_observed: pending queue items, unpasted handoffs, unreviewed plans |
| operating expense | turns, tokens, context budget, and executor dispatches |
| constraint | the most binding element currently gating goal progress |

The Five Focusing Steps:
1. Identify — name the most binding constraint gating the goal from recorded state
2. Exploit — observe the pending item before preparing another; aim full attention at the most blocking unsatisfied criterion
3. Subordinate — pace non-constraint lanes to the constraint; idle-and-ready beats producing inventory
4. Elevate — only after exploit+subordinate still leave the constraint binding, add capacity (raise turn ceiling, add executor)
5. Repeat — after any constraint resolves, re-identify; don't keep optimizing yesterday's blocker

Anti-patterns:
- Robot-line fallacy: celebrating lane output (plans drafted, handoffs prepared) while observed completions stay flat
- Inventory blindness: treating prepared_not_observed growth as progress — it is cost
- Balanced-line fallacy: trying to keep every lane equally busy; constraint-first deliberately runs non-constraint lanes idle

## Measured Loop Discipline

Use when the loop goal has a single measurable signal. All three conditions must hold for a loop to be measurable:
- A command runs unattended to completion — no prompts, no manual setup
- It reports exactly one number (several signals may feed it, but the loop compares one value)
- The number has a declared direction: higher_is_better or lower_is_better

If any condition fails, the loop is unmeasured — say so plainly and use verification gates (tests, review, named acceptance criteria) instead. Note: the existing Stopping Conditions table uses AND-combined signals ("all tickets done AND tests green") which are composite gates, not single-number metrics. That is correct — composite gates are the right stopping mechanism for unmeasured loops.

A fabricated metric is worse than none — it makes arbitrary discard decisions look principled.

Fix the evaluation contract before the first attempt. Record it as loop-held state:
- command: the exact unattended command that produces the score
- metric: what the single number counts
- direction: higher_is_better or lower_is_better
- harness_mutable: false — the contract is fixed for the run
- baseline: the metric value before the first attempt

The loop may not edit the scoring harness, its fixtures, or the metric definition. Raising the score by changing what the score means is not an improvement. Note: this applies to external eval harnesses, not to the self-improving skills pattern elsewhere in this skill — skill improvement writes to the staging path, not to the scoring harness.

## Round-Trip Validation + Conditional Re-Loop (Denuto Pattern)

Source: Denuto `denuto-tenderiser/scripts/ralph_loop.py`

Full self-healing loop with conditional re-assembly:

```
Step 1: Load profile / task definition
Step 2: Evaluate rules → manifest (what to produce, what constraints apply)
Step 3: Fetch/generate artifact (LLM call or external source)
Step 4: Validate (round-trip) — run the artifact through a validator
Step 5: Check findings
  - If critical findings exist AND loop_count < max_loops:
      Apply fixes to artifact → go back to Step 3 with context of failures
  - Else: break (either clean or max_loops reached)
Step 6: Report final artifact + loop history
```

```python
def ralph_loop(profile, max_loops=3):
    manifest = evaluate_rules(profile)
    loop_history = []

    for loop_count in range(max_loops):
        artifact = generate_artifact(manifest, previous_failures=loop_history)
        findings = validate_artifact(artifact, manifest)
        critical = [f for f in findings if f["severity"] == "critical"]
        loop_history.append({"loop": loop_count, "findings": len(findings), "critical": len(critical)})
        if not critical:
            break  # Clean — exit early

    return artifact, loop_history
```

**Key invariants**:
- `max_loops` always respected — never infinite
- Loop history carried forward as context — each iteration knows prior failures
- Validator is read-only — never mutates the artifact
- Zero-critical exits early (don't waste loops)

**Hermes adaptation** — generate → validate → fix pattern:
- Code generation → test runner → fix → re-run
- Skill draft → adversarial-review → fix → re-review
- Research → coherence check → patch gaps → re-check

See also: `hermes-improvement-governance` for risk-gated deployment of loop results.

Keep/discard rules per cycle:
- Better metric: keep
- Worse metric: discard, reset, next attempt
- Crash or non-zero exit from scoring command: discard and log cycle status=crash; never silently retry
- Equal metric: keep the simpler change — less code at the same score is a win

<!-- why: harness-immutability prevents the common failure mode of gaming the eval by changing what the score means -->

## Harness-Update Phase (Evo-Harness, arXiv:2608.15071)

After the loop completes, run once:
1. Extract cross-domain lessons from the full trajectory (generalizable, not task-specific).
2. Propose a skill/harness update candidate — do not auto-apply; flag for human review.
3. Skip if the loop produced fewer than 3 similar tasks (insufficient signal for reliable harness update).
