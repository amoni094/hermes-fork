# Math Research Pipeline — Adversarial Check Patterns

For reviewing patches derived from a mathematical primers → paper classification → spike
experiments → system implementation pipeline. These checks supplement standard code review.

## Authority Laundering Check

ArXiv IDs in comments are not tests. Validate math-to-code translation:

1. State the mathematical object the code claims to implement
2. Find the key formula or boundary condition in the code  
3. Check at least one edge case numerically against the primer's analytic result
4. Verify the code handles the boundary cases (k=0, k=n, empty input, cold start)

## Vocabulary Abuse — Most Common KILL Signal

The single most frequent kill reason in book-derived proposals: optimization or control
terminology applied to the wrong mathematical object. Generates false guarantees.

Pattern check — for each proposed implementation, ask:
- Does the code's input MATCH the mathematical object the term describes?
  - 'Armijo backtracking' requires a gradient and step-direction (PID error delta ≠ gradient)
  - 'Lipschitz contraction' requires two states and a distance-preserving map (ratio of two
    deltas ≠ Lipschitz constant; contraction requires a fixed point and metric)
  - 'Duality gap certificate' requires a Lagrangian and dual feasibility (heuristic gap ≠ bound)
  - 'Value iteration eps-halt' requires a Bellman operator (PID step ≠ Bellman iterate)
  - 'Span seminorm' requires the range of a real-valued function on state space (error range
    of a PID loop is NOT a span seminorm unless the error function is a value function)
  - 'Upcrossing' (Doob's theorem) requires a supermartingale — monotone convergence is
    not sufficient; the error series must satisfy the supermartingale property
- If the input does not match: KILL or WEAKEN to remove the mathematical name
  and restate the check as a general heuristic.

Vocabulary abuse is always a KILL or WEAKEN — never a KEEP with a caveat. False names
in comments/docstrings create compounding misunderstanding across future readers.

Concrete batch (Sep 2026, 24 proposals): 13/24 killed; vocabulary abuse was the
primary or contributing reason in ~8 of those kills.

## Specific Failure Modes (Sep 2026 batch, 20 patches)

### Clopper-Pearson lower bound edge case

Wrong: `if k == n: return 1.0`
Correct: `if k == n: return (alpha / 2) ** (1.0 / n)`

At n=7, k=7, alpha=0.05: wrong gives 1.0, correct gives ~0.59. CP lower bound is
never 1.0 without infinite data. Both gepa_skill_eval.py and skillopt_score.py had
the same bug (identical copy). `return 1.0` inside `_betainc` (for x>=1) is correct;
only the outer k==n guard was wrong.

Numerical spot-check: for any CP implementation, verify:
  cp_lower(0, 5) == 0.0         # k=0 boundary
  0.55 < cp_lower(7, 7) < 0.65  # k=n boundary (not 1.0)
  0.3 < cp_lower(3, 5) < 0.7   # midpoint plausibility

### LTL schema mismatch (detection vs authorization)

A classify/detect command that logs `approved=False` always will corrupt a safety verifier
that checks `action_induced AND NOT approved`. The verifier fires on every detection event.

Fix pattern: LTL verifier must scope to `cmd=check` (authorization) records only, never
`cmd=classify` (detection) records. Or: detection commands must not set `approved` at all.

Check: if `ltl-check` raises violations immediately on fresh sessions that only ran
`classify`, this bug is present.

### Live blend with no state file writer (dead math on hot path)

A score blend like `0.6*tfidf + 0.4*posterior_mean(state)` is benign when state is empty
(posterior defaults to 0.5, compressing scores without changing rank), but it is dead
math until something writes the state file.

Check: for any statistical posterior or learned weight file, verify a *writer* exists
in the same codebase. If absent, gate the blend:
  `score = (0.6*tfidf + 0.4*posterior) if state_nonempty else tfidf`

### Provenance/metadata injected into fact text

Any field written into fact bullet text (e.g. `[chain_hash=abc123]`) becomes part of the
fact key used by promote pipelines for recurrence counting. Unique values per write =
recurrence count always 1 = facts never stage.

Rule: hash chains, IDs, and provenance metadata go into sidecar files or DB columns only,
never into the fact text itself. Check l1-promote's key extraction logic (`fact[:60]`,
`fact[:240]`) to confirm no metadata bleeds into the key window.

### Skip gate applied inconsistently across code paths

A filter that drops low-value facts (rv=0) must be applied uniformly across ALL call paths:
single-call path, batch path, and the append_facts function. Exemptions for high-value
types (correction, outcome, preference) must be enforced at ALL entry points.

Check: search for every place the filter condition can be reached and verify the same
exemption logic fires. Use a shared `should_keep(fact)` function, not inline conditions.

## Implemented-but-Killed Verdict Application

When adversarial and implementation subagents run in parallel and the critic kills a proposal
that was already implemented:

**Do NOT remove the code.** Remove only the false mathematical claim:
1. Rewrite the docstring to remove the mathematical name and authority claim.
   Replace with a plain statement of what the heuristic does.
2. Demote FAIL/HALT to WARN for checks the runtime cannot enforce (type checker absent,
   external validator absent, model internals unavailable).
3. Remove KILL-class action overrides (e.g. BLOCK verdict based on a false MDP guarantee;
   leave the gate as advisory WARN output instead).
4. Re-run `python3 -m py_compile` on every modified file.
5. Add an explicit disclaimer in the docstring that this is a general-purpose heuristic,
   not a certified guarantee from the cited framework.

**The WEAKEN path:** When the critic's verdict is WEAKEN rather than KILL, implement the
simplest form that passes the critic's objection:
- If objection is 'infrastructure missing': remove the logic that requires the missing
  infrastructure, keep the observable heuristic it was approximating.
- If objection is 'vocabulary abuse': rename the function/parameter to neutral names,
  remove the mathematical claim from docstring, keep the numerical rule.
- If objection is 'FAIL too strict for a WARN': always demote — do not argue with the critic.

**Parallel dispatch rule:** Adversarial subagent and implementation subagent CAN run in
parallel on the same proposal batch. Merge order: apply adversarial verdicts after
implementation is confirmed via py_compile. The implementation subagent may produce
more output than needed — verdict application is always surgical (strip, not revert).

## Verification Script Pitfall: Comment False Positive

When checking source code for prohibited patterns, strip inline comments before the check.
A comment like:
  `return 1  # H6 fix: was sys.exit(1) — let caller handle`
contains `sys.exit(` as a string but is not a live call.

Pattern:
```python
import re
def strip_comments(code): return re.sub(r'#[^\n]*', '', code)

# Use full function boundary, not fixed char window
fn_start = src.find('def my_function(')
next_def = src.find('\ndef ', fn_start + 10)
fn_body = src[fn_start:next_def]
fn_nc = strip_comments(fn_body)  # comment-stripped version for live-call checks

chk('sys.exit(' not in fn_nc, 'no live sys.exit call')
```

## Infrastructure Precondition Check

Before declaring an implementation complete, verify its preconditions exist:

| Feature | Required precondition |
|---|---|
| FTRL / online learner | State file writer that emits losses per example |
| Beta posterior routing | Writer that records task_ok/fail signals per skill |
| Hash chain integrity | Persistent last-digest storage (not process-local dict) |
| SimHash dedup | Cross-run seen-papers cache (process-local catches intra-run only) |
| Kalman/CUSUM latency | Per-tool baseline history persisted across invocations |
| FOK/JOL calibration | calibration_log.jsonl writer that appends (session_id, task_class, fok_score, jol, decision, outcome=null) |
| SDT d-prime diagnostic | Requires calibration_log.jsonl with n>=50 labeled rows per L-class PLUS human-verified outcome labels — outcome=null rows are unusable |
| Conformal prediction routing | Requires labeled outcome stream with outcome_success=bool in cobra-outcomes.jsonl; result_used=null is not a label |
| Stopping rules based on error martingales | Requires error to satisfy the supermartingale property — check that the error process is demonstrably non-increasing in expectation before applying Doob's theorem |
| Backward induction / MDP lookahead | State space must be enumerable and transitions deterministic or explicitly modeled — not applicable to arbitrary natural-language context |

**Shared-log SPOF warning:** When multiple spikes depend on the same precondition log file,
if that file is missing or unlabeled, ALL dependent spikes fail simultaneously. Identify
shared-log dependency chains before declaring any of the spikes implementable.

Concrete case (Sep 2026): FOK calibration (Spike M), SDT diagnostic (Spike N), and
conformal routing (Spike L) all required calibration_log.jsonl or outcome_success labels
that didn't exist. Critic correctly noted: "if that log is invented without verified
outcomes, all three produce false calibration and can disable or retune gates together."
Fix: build the writer for the foundational log first (Spike M), then gate downstream
spikes (N, L) on reaching n>=50 labeled rows before enabling their logic.

Ordering rule: when spikes share a log dependency, implement them in sequence (log writer
first), never in parallel. Parallel implementation on a shared nonexistent log means all
spikes go live reading from an empty or unlabeled file.

**Calibration log writer pattern (additive, non-breaking):**
When adding a new instrumentation log to an existing script:
- Add optional CLI args (e.g. `--session`, `--task-class`) with `default=None`; do not
  make them required — existing callers without those args must not break.
- The writer fires ONLY when the session-anchor arg is present; no-arg calls are silent.
- Set `outcome=null` in every row written by the instrument — never auto-infer outcome.
  Outcome labels must come from a separate verified external signal (human correction,
  test pass, verified tool result). Writing `outcome=True` from within the instrument
  itself creates circular validation.
- Wrap the writer in `try/except OSError: pass` so logging failures never crash the harness.

Missing precondition = the feature is a stub, not an implementation. Either build the
writer in the same batch, or gate behind `if state_file_exists`.

## Cross-Corpus Kill Revival — Infrastructure Precondition Check

When a book-corpus proposal was killed with verdict "infrastructure missing", revivability
depends on what was built since the kill. Check before each new implementation wave:

| Kill reason | Revival condition | Permanent kill (never revive) |
|---|---|---|
| Missing log/file | Log writer now exists AND has been running for N sessions | — |
| Missing DB column | Column added and being populated | — |
| Vocabulary abuse / wrong object | n/a | Always permanent — do not revive |
| Infrastructure not adjoint pair | n/a | Always permanent — wrong mathematical structure |
| Missing model internals (logits, gradients) | n/a | Permanent in prompting-only context |

Revival gate: (a) blocking file/subcommand exists in production and has been running,
(b) implementation is additive and diagnostic-only. Both required.

**Cross-corpus synergy proposals** (from book-corpus × arXiv sweep intersection) have no
single source to review. Apply the same infrastructure check: verify all shared
preconditions are live before implementing either side of the intersection.

Shared-SPOF rule applies equally: if two cross-corpus synergy proposals both read the
same precondition file (e.g. skill-sequences.jsonl), and that file is empty or missing,
both fail simultaneously. Implement the writer in the same batch as the readers.

## System Surface Mapping

Apply math findings to ALL system surfaces, not skills alone:

  ~/.hermes/scripts/*.py   — runtime scripts, memory pipeline, cron scripts
  ~/.hermes/config.yaml    — retry budgets, concurrency limits, model routing
  ~/.hermes/cron/jobs.json — scheduling, stagger, pipeline ordering
  ~/.hermes/memory-facts/  — retention policy, fact scoring thresholds

For each finding: "which script/config component has the analogous structure?"
A finding that only patches a skill file is likely missing its real leverage point.

## Skipped-Item Feasibility Verdicts (Sep 2026)

Permanently infeasible in a prompting-based agent framework (do not reopen):
  Fourier PE, Gluon/LMO training, PAC-MDP on language-state crons, geometric
  equivariant nets, Grover/quantum, bandits on safety quarantine.

Implementable but assumption fails (not worth building):
  LinUCB at K~200 skills (exploration tax exceeds T; use Beta per-cluster instead),
  RIP/compressed sensing at N=208 (random projection doesn't create CS problem),
  PAC on K=3 dependent confirms (n=3 gives Hoeffding half-width ~0.55 = vacuous).
