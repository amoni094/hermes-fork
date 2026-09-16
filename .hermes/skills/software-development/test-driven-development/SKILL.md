---
name: test-driven-development
related_skills:
  - workflow-map
  - systematic-debugging
  - complexity-gated-planning
  - isolated-workspace-preflight
  - requesting-code-review
  - verification-before-completion
  - plan
  - subagent-driven-development

depends_on: [plan, complexity-gated-planning]
provides: [tdd, red-green-refactor, test-first-development]
triggers:
  - User wants tests written before the implementation code
  - Need to enforce RED-GREEN-REFACTOR discipline on a coding task
  - User says 'TDD', 'write tests first', or 'test-driven'
  - Starting a feature or bug fix where the correct behavior must be specified as tests before coding
description: >
  Use when: TDD: enforce RED-GREEN-REFACTOR, tests before code.
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, tdd, development, quality, red-green-refactor]
    related_skills: [workflow-map, systematic-debugging, complexity-gated-planning, isolated-workspace-preflight, requesting-code-review, verification-before-completion, plan, subagent-driven-development]
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Default for most behavior-changing work:**
- New features
- Bug fixes
- Refactoring that changes observable behavior
- Behavior changes with a clear test surface

**Usually not the primary workflow:**
- read-only investigation
- documentation-only edits
- pure configuration or metadata changes with no meaningful executable test surface
- throwaway prototypes the user explicitly wants kept lightweight

**Ask the user before skipping TDD when code behavior is changing.**
If the task still changes production behavior but TDD seems awkward, that is a signal to justify the exception explicitly rather than silently downgrading the workflow.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

## Red-Green-Refactor Cycle

### RED — Write Failing Test

Write one minimal test showing what should happen.

**Good test:**
```python
def test_retries_failed_operations_3_times():
    attempts = 0
    def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception('fail')
        return 'success'

    result = retry_operation(operation)

    assert result == 'success'
    assert attempts == 3
```
Clear name, tests real behavior, one thing.

**Bad test:**
```python
def test_retry_works():
    mock = MagicMock()
    mock.side_effect = [Exception(), Exception(), 'success']
    result = retry_operation(mock)
    assert result == 'success'  # What about retry count? Timing?
```
Vague name, tests mock not real code.

**Requirements:**
- One behavior per test
- Clear descriptive name ("and" in name? Split it)
- Real code, not mocks (unless truly unavoidable)
- Name describes behavior, not implementation

### Verify RED — Watch It Fail

**MANDATORY. Never skip.**

```bash
# Use terminal tool to run the specific test
pytest tests/test_feature.py::test_specific_behavior -v
```

Confirm:
- Test fails (not errors from typos)
- Failure message is expected
- Fails because the feature is missing

**Test passes immediately?** You're testing existing behavior. Fix the test.

**Test errors?** Fix the error, re-run until it fails correctly.

### GREEN — Minimal Code

Write the simplest code to pass the test. Nothing more.

**Good:**
```python
def add(a, b):
    return a + b  # Nothing extra
```

**Bad:**
```python
def add(a, b):
    result = a + b
    logging.info(f"Adding {a} + {b} = {result}")  # Extra!
    return result
```

Don't add features, refactor other code, or "improve" beyond the test.

**Cheating is OK in GREEN:**
- Hardcode return values
- Copy-paste
- Duplicate code
- Skip edge cases

We'll fix it in REFACTOR.

### Verify GREEN — Watch It Pass

**MANDATORY.**

```bash
# Run the specific test
pytest tests/test_feature.py::test_specific_behavior -v

# Then run ALL tests to check for regressions
pytest tests/ -q
```

Confirm:
- Test passes
- Other tests still pass
- Output pristine (no errors, warnings)

**Test fails?** Fix the code, not the test.

**Other tests fail?** Fix regressions now.

### REFACTOR — Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers
- Simplify expressions

Keep tests green throughout. Don't add behavior.

**If tests fail during refactor:** Undo immediately. Take smaller steps.

### Repeat

Next failing test for next behavior. One cycle at a time.

## Why Order Matters

**Decision-theoretic test value (MacKay Ch 36):** A test has value only if it can change
the action taken (i.e., cause you to fix the code). A test written after the code whose
outcome you can predict with certainty before running adds zero information. The red
phase is not a ritual -- it is the only way to confirm the test has non-zero information
value: you observe an outcome (failure) you did not already know.

"I'll write tests after to verify it works"

Tests written after code pass immediately. Passing immediately proves nothing:
- Might test the wrong thing
- Might test implementation, not behavior
- Might miss edge cases you forgot
- You never saw it catch the bug

Test-first forces you to see the test fail, proving it actually tests something.

**"I already manually tested all the edge cases"**

Manual testing is ad-hoc. You think you tested everything but:
- No record of what you tested
- Can't re-run when code changes
- Easy to forget cases under pressure
- "It worked when I tried it" ≠ comprehensive

Automated tests are systematic. They run the same way every time.

**"Deleting X hours of work is wasteful"**

Sunk cost fallacy. The time is already gone. Your choice now:
- Delete and rewrite with TDD (high confidence)
- Keep it and add tests after (low confidence, likely bugs)

The "waste" is keeping code you can't trust.

**"TDD is dogmatic, being pragmatic means adapting"**

TDD IS pragmatic:
- Finds bugs before commit (faster than debugging after)
- Prevents regressions (tests catch breaks immediately)
- Documents behavior (tests show how to use code)
- Enables refactoring (change freely, tests catch breaks)

"Pragmatic" shortcuts = debugging in production = slower.

**"Tests after achieve the same goals — it's spirit not ritual"**

No. Tests-after answer "What does this do?" Tests-first answer "What should this do?"

Tests-after are biased by your implementation. You test what you built, not what's required. Tests-first force edge case discovery before implementing.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "Test hard = design unclear" | Listen to the test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD faster than debugging. Pragmatic = test-first. |
| "Manual test faster" | Manual doesn't prove edge cases. You'll re-test every change. |
| "Existing code has no tests" | You're improving it. Add tests for the code you touch. |

## Red Flags — STOP and Start Over

If you catch yourself doing any of these, delete the code and restart with TDD:

- Code before test
- Test after implementation
- Test passes immediately on first run
- Can't explain why test failed
- Tests added "later"
- Rationalizing "just this once"
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "Keep as reference" or "adapt existing code"
- "Already spent X hours, deleting is wasteful"
- "TDD is dogmatic, I'm being pragmatic"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered
- [ ] Optimizer/solver tests assert KKT (or `∇f≈0` / duality gap), not just that the objective decreased
- [ ] Monadic pipelines: each Kleisli arrow tested in isolation before the composed chain (Milewski Ch 4, Ch 20.1)

Can't check all boxes? You skipped TDD. Start over.

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write the wished-for API. Write the assertion first. Ask the user. |
| Test too complicated | Design too complicated. Simplify the interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify the design. |

## Integration with Other Skills

When a test passes after a fix, verify causation before declaring it resolved:
  ```
  python3 ~/.hermes/scripts/metacognitive-harness.py causal-check \
    --observation "test Y now passes" --candidate-cause "fix X" \
    --evidence "<before/after test output>"
  ```
  Exit 1 (CORRELATED): the test passes but causation is unconfirmed — check for pre-existing fixes or flaky tests.

Before marking a test suite complete, run boundary-check to confirm all required cases are covered:
  ```
  python3 ~/.hermes/scripts/metacognitive-harness.py boundary-check \
    --task "test coverage for <feature>" --action "<tests written>"
  ```
  Exit 1: additional tests still needed. Exit 2: OVER_ACTION. Exit 3: SCOPE_CREEP beyond the declared test target.

**complexity-gated-planning:** Decide first whether the task deserves a formal plan or can go straight into a tight TDD loop.

**plan:** For larger changes, use plan mode to define the implementation path before starting RED-GREEN-REFACTOR cycles.

**isolated-workspace-preflight:** When the TDD work will touch many files, risky repo state, or parallel feature work, decide whether to start from an isolated Hermes worktree first.

**requesting-code-review:** After the implementation turns green, use this for an independent review and baseline-aware verification before commit/push.

**verification-before-completion:** Do not claim the fix or feature is done just because the target test passed once. Use this to require fresh end-to-end evidence before finalizing.

## Hermes Agent Integration

### Running Tests

Use the `terminal` tool to run tests at each step:

```python
# RED — verify failure
terminal("pytest tests/test_feature.py::test_name -v")

# GREEN — verify pass
terminal("pytest tests/test_feature.py::test_name -v")

# Full suite — verify no regressions
terminal("pytest tests/ -q")
```

### With delegate_task

When dispatching subagents for implementation, enforce TDD in the goal:

```python
delegate_task(
    goal="Implement [feature] using strict TDD",
    context="""
    Follow test-driven-development skill:
    1. Write failing test FIRST
    2. Run test to verify it fails
    3. Write minimal code to pass
    4. Run test to verify it passes
    5. Refactor if needed
    6. Commit

    Project test command: pytest tests/ -q
    Project structure: [describe relevant files]
    """,
    toolsets=['terminal', 'file']
)
```

### With systematic-debugging

Bug found? Write failing test reproducing it. Follow TDD cycle. The test proves the fix and prevents regression.

Never fix bugs without a test.

### Counterfactual test for a bug fix (Pearl)

For each bug fix, write the counterfactual test: "if the fix were absent, this test fails." Watch RED on the unfixed code, GREEN on the fixed code. A fix without a failing-before / passing-after test is not verified — a test that would also pass without the fix is not evidence of causation.
<!-- why: prevents declaring a fix verified when the test never could have failed -->

## Vertical Slices (Tracer Bullets) — Do Not Horizontal Slice

DO NOT write all tests first, then all implementation. This is horizontal slicing and produces bad tests:
- Tests written in bulk test imagined behavior, not actual behavior
- You end up testing the shape of things rather than user-facing behavior
- You outrun your headlights, committing to test structure before understanding the implementation

CORRECT approach — vertical slices via tracer bullets:
- One test → one implementation → repeat
- Each test responds to what you learned from the previous cycle
- Because you just wrote the code, you know exactly what behavior matters

```
WRONG (horizontal):
RED: test1, test2, test3, test4, test5
GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
RED→GREEN: test1→impl1
RED→GREEN: test2→impl2
RED→GREEN: test3→impl3
```

## Property Tests as Theorems (Thompson)

Propositions-as-types: a property-based test is an executable proposition.
Frame each property as a theorem to be proved — inhabited for every generated
input — not a check that happened to pass on this run. Name it as a claim
(`sort_is_ordered`, `decode_inverts_encode`), state the universal quantifiers
(the generators) and the conclusion (the assertion). A property that only
encodes "did not throw" is an empty type inhabited by `pass`. <!-- why: prevents property tests that confirm execution rather than prove an invariant -->

## Sequential stopping for property-based tests (Wald SPRT)

Do not run a fixed number of property-based samples. SPRT is statistically
optimal: accumulate the likelihood ratio of "property holds" vs "property
fails" and stop as soon as it exits (B, A). Fixed-N either wastes trials after
the decision is already determined or stops without controlling α and β.

Pre-assign α (declare fail when the property holds) and β (declare hold when it
fails). Continue only while B < Λ_n < A, with A ≈ (1−β)/α and B ≈ β/(1−α).
Truncate at a hard n_max if wall-clock requires it — untruncated SPRT is the
benchmark, not always the deployed loop. See `wald-sequential-analysis`.
<!-- why: Wald Ch 3: SPRT minimizes E(n) among tests with given Type I/II errors -->

## Type I vs Type II errors in the suite (Wald)

Every test suite has an implicit α (false positive: fail when the code is
correct) and β (false negative: pass when the code is wrong). Treating all
failures as equally important ignores this tradeoff.

- **Flaky tests** — high α. Fix isolation, determinism, timing. Do not add more
  of the same tests; that inflates α further.
- **Coverage gaps** — high β. Add tests that would fail on the missing behavior.
- You cannot drive both α and β to 0 without unbounded sample size (Wald: error
  bounds set A, B and thus expected N).

Diagnose which error a failure is before choosing the fix.
<!-- why: Wald Ch 2–3: α and β are distinct, preassigned, and trade off against ASN -->

## Anti-Tautological Tests

Expected values must come from an independent source of truth — a known-good literal, a worked example, the spec. Never compute the expected value the same way the code computes it.

Tautological (worthless):
```python
expect(add(a, b)).toBe(a + b)  # can never catch a wrong implementation
```

Good:
```python
expect(add(2, 3)).toBe(5)  # independent literal
```

If the expected value is computed the same way the code computes it, the test can never disagree with the code — break the code wrong and the assertion breaks wrong with it.

## Optimality certificates for planners and agent policies

Threshold tests ("agent score > X") do not certify a planning/MDP solution. For code that
claims an optimal value or policy, tests must check **Bellman optimality conditions** at
the reported solution (Puterman 6.2; see `puterman-mdp`):

- Residual: `v ≈ T v` (sup-norm or span of the Bellman residual below tolerance).
- Greedy: the reported policy attains the max in the Bellman operator at every state
  (or every sampled state, with the sampling policy stated).
- Horizon: finite-horizon solutions are checked per time index `v_t = T_t v_{t+1}`, not
  with a single stationary residual.

A high episodic return with a large Bellman residual is a failed certificate, not a pass.

## Invariant tests for algorithms (CLRS 4th ed, §2.1)

For loops and iterative algorithms, a suite that only asserts the **final output** is incomplete. CLRS proves correctness with a loop invariant in three steps; the tests must match that proof, not just the postcondition.

For the invariant I of a non-trivial loop, the suite must include:

1. **Initialization** — I holds before the first iteration (empty prefix, i at the start value, heap property after build, etc.).
2. **After one iteration** — I still holds (catches off-by-one and broken maintenance that luck into a good last state on the usual fixtures).
3. **Termination** — at exit, I plus the exit condition imply the postcondition (the full output assertion).

Example: insertion sort (CLRS §2.1) — assert the prefix `A[1..i-1]` is the original prefix in sorted order at i=2 (init), after the first insert, and when i=n+1 (sorted array). A single `assert sort(xs) == sorted(xs)` does not witness initialization or maintenance.

Prefer exposing the invariant through a **public test hook or a pure helper function** — not private field access. This is compatible with the DPI rule: the hook is an *intentional* layer boundary. Property-based tests can check I on random prefixes; they do not replace the three proof points.

If no such hook exists, add a minimal, pure, side-effect-free method (e.g. `is_heap_property_satisfied()`) that the production code also uses for assertions. This is not a DPI violation — it is a deliberate interface extension for invariant observability.

<!-- why: loop-invariant tests and DPI are compatible when the invariant is observed via a public hook, not via internal field inspection. -->

## Calibration Tests for Probabilistic Outputs

Predicted probability p must match empirical frequency p (Jaynes: the honest weatherman). Any code that outputs probabilities, confidences, or calibrated scores needs calibration tests, not only accuracy tests:
- Reliability diagram or expected calibration error (ECE) on a held-out set: in the bin of predicted p ≈ 0.8, about 80% of events should occur.
- A model with high accuracy and poor calibration is not emitting probabilities; do not wire those numbers into thresholds, expected-loss decisions, or Bayes updates until they are calibrated (or explicitly labeled uncalibrated).
- RED: write a calibration assertion that fails on a known-miscalibrated stub. GREEN: the implementation meets the ECE/reliability bound. Do not skip this for "soft" classifiers, ranking scores sold as probabilities, or LLM confidence fields.

**Role separation for AI-assisted TDD (ExecCritic, arXiv:2609.09133):** When AI writes both
code and tests in the same context window, the tests are subject to the same blind spots as the
code. The same-agent combination degrades resolve rate vs separated roles. Mitigation:
- Tests must be committed and runnable (failing red) BEFORE the implementation pass starts.
- The implementation agent sees test output (pass/fail) but NOT the test source as an editable target.
- A green suite after the implementation agent edited tests is false confidence — treat as fail.
  Check via: `git diff HEAD -- tests/` after repair; any diff is an ExecCritic violation.

**ML code: the test suite must include a CV harness (Hastie ESL Ch 7.10).** A model
evaluated on the same observations it was trained on is a tautological test — identical
in kind to computing the expected value the same way the code computes it, and identical
to the same-agent code+tests problem above. Train-set accuracy/loss is not a test.
Require K-fold (typically 5 or 10) or a vaulted holdout that never influenced
preprocessing, feature selection, or hyperparameter search. All of those steps sit
*inside* each training fold (wrong-way CV: screen on all N, then CV the classifier —
ESL's noise-feature toy reports ~3% CV error vs 50% true). Complexity-parameter
selection is training; only the selected model is assessed.

## Tests Through Public Interfaces Only

Tests should verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

- Good: exercise real code paths through public APIs
- Bad: mock internal collaborators, test private methods, verify through external means

Warning sign: your test breaks when you refactor, but behavior hasn't changed. That test was testing implementation, not behavior.

**DPI grounding (Cover & Thomas, Ch 2):** Each abstraction layer reduces available information
(I(X;Z) <= I(X;Y) for chain X->Y->Z). A test that reaches through the abstraction boundary
into implementation details is accessing information that the layer was designed to hide.
When the implementation changes, that test breaks even though the public contract is unchanged
-- it is a DPI violation: the test was using information that should not be observable from
its layer. Test only at the layer boundary where information is intentionally exposed.

## Kleisli arrows before the pipeline (Milewski Ch 4, Ch 20.1)

A monadic pipeline (`Promise`/`Task` chains, `flatMap`, `Result`/`Either` binds, `do` blocks) is Kleisli composition of arrows `a → m b`. Each arrow is a function in its own right; composition (`>=>` / bind) is a separate, lawful operation. Writer-style embellishment (logs, errors, state) is combined *outside* the steps — "the aggregation of the log is no longer the concern of the individual functions" (Ch 4).

**TDD order:**
1. RED-GREEN each Kleisli arrow in isolation (pure `a → m b`: given `a`, assert the `m b`). Cover identity cases (`return`) where the pipeline has units.
2. Only then RED-GREEN the composed pipeline (fish / bind / `then`). Associativity is the integration property: `(f >=> g) >=> h` vs `f >=> (g >=> h)` must agree (Ch 20.1).

Do not skip step 1. A green end-to-end pipeline with untested steps cannot tell you *which* arrow broke, and cannot witness that composition (not a hidden global) is doing the embellishment.

This is vertical slicing applied to Kleisli: one arrow → one test cycle, then one composition → one test cycle. Horizontal "test the whole `do` block first" is the same defect as writing all tests before any implementation.

## Typecheck and Test Run Discipline

During implementation:
- Run typechecking regularly (after each meaningful change, not just at the end)
- Run single test files regularly (fast feedback)
- Run the full test suite ONCE at the end (to check for regressions)

## Testing Anti-Patterns

- **Testing mock behavior instead of real behavior** — mocks should verify interactions, not replace the system under test
- **Testing implementation details** — test behavior/results, not internal method calls
- **Happy path only** — always test edge cases, errors, and boundaries
- **Brittle tests** — tests should verify behavior, not structure; refactoring shouldn't break them
- **Objective decreased ≠ valid solution** — tests for optimization code must verify KKT conditions (or unconstrained stationarity `∇f ≈ 0` / Newton decrement) at the reported solution, not just that the objective dropped. A decreasing objective that violates KKT is not a valid solution (Boyd 5.5.3). Constrained solvers: also assert duality gap within tolerance.

## Final Rule

```
Production code → test exists and failed first
Otherwise → not TDD
```

No exceptions without the user's explicit permission.
