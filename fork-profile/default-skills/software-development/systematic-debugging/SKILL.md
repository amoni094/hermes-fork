---
name: systematic-debugging
related_skills:
  - test-driven-development
  - plan
  - subagent-driven-development
  - adaptive-agent-reasoning

depends_on: [plan, verification-before-completion]
provides: [root-cause-analysis, bug-reproduction, systematic-debugging]
triggers:
  - A bug exists and the root cause is unknown — need a structured 4-phase debugging approach
  - User says 'debug this', 'find the bug', or 'why is this failing'
  - Debugging a complex failure where the first instinct is to start patching without understanding
  - Need to understand the bug before fixing it (reproduce → isolate → root cause → fix)
description: >
  Use when: 4-phase root cause debugging: understand bugs before fixing.
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, plan, subagent-driven-development]
ssl_scheduling:
  triggers:
    - Bug exists with unknown root cause
    - User says 'debug this', 'find the bug', or 'why is this failing'
    - Complex failure where instinct is to patch without understanding
    - Need reproduce → isolate → root-cause → fix before any fix attempt
  preconditions:
    - Access to the codebase or system exhibiting the bug
    - Ability to run or observe the failing system
  estimated_steps: 12
ssl_structural:
  tools_used: [terminal, read_file, search_files, browser_navigate, web_search]
  subtasks:
    - Phase 1 — Reproduce (confirm failure is real and repeatable)
    - Phase 2 — Isolate (narrow to the smallest failing case)
    - Phase 3 — Root-cause analysis (trace to the actual source)
    - Phase 4 — Fix and verify (patch then re-run full suite)
ssl_logical:
  side_effects:
    - May run test suites or build commands
    - May write diagnostic scripts or minimal reproducers
  resources:
    - Project source tree
    - Test runner configuration
    - Log files / observability output
  risk_level: low
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Debugging is Bayesian inference (Jaynes).** Start with a prior over possible bug locations (recent changes, error messages, stack frames). Update on each observation (test result, log line, bisect step). The posterior is your next hypothesis. Skipping to a confident diagnosis without evidence is assigning a degenerate prior — certainty by fiat. One hypothesis at a time is sequential Bayes, not indecision; a hypothesis you refuse to update after contrary evidence is ideology, not inference.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 0. Build a Tight Feedback Loop First

**This is the skill. Everything else is mechanical.**

If you have a tight pass/fail signal for the bug — one that goes red on *this* bug — you will find the cause. If you don't, no amount of reading code will save you. Spend disproportionate effort here before moving on.

**AEP principle (Cover & Thomas, Ch 3): test the actual failure, not an imagined variant.**
The Asymptotic Equipartition Property says most inputs from a distribution lie in the
typical set. Bugs found in production are typically typical -- they occur on common inputs.
When building your feedback loop, reproduce the actual failing input/state, not a
simplified stand-in you think should behave the same. Stand-ins often miss the specific
typical-set member that triggers the bug. Reproduce the exact scenario; then simplify
only once the loop is working.

**Ways to construct one — try in roughly this order:**
1. Failing test at whatever seam reaches the bug (unit, integration, e2e)
2. `curl` / HTTP script against a running dev server
3. CLI invocation with a fixture input, diffing stdout against a known-good snapshot
4. Headless browser script (Playwright/Puppeteer) — drives the UI, asserts on DOM/console/network
5. Replay a captured trace — save a real network request/payload/event log to disk, replay in isolation
6. Throwaway harness — minimal subset of the system that exercises the bug code path with one function call
7. Property/fuzz loop — if the bug is "sometimes wrong output", run 1000 random inputs and look for the failure mode
8. Bisection harness — if the bug appeared between two known states, automate "boot at state X, check, repeat"

**Tag any debug logs you add** with a unique prefix (e.g. `[DEBUG-a4f2]`). Cleanup at the end becomes a single grep; untagged logs linger indefinitely.

**Tighten the loop once you have one:**
- Can I make it faster? (cache setup, narrow scope)
- Can I make the signal sharper? (assert the specific symptom, not "didn't crash")
- Can I make it deterministic? (pin time, seed RNG, freeze network)

A 30-second flaky loop is barely better than no loop; a 2-second deterministic one is a debugging superpower.

**Completion criterion — you must be able to name one command that you have run at least once and that is:**
- [ ] **Red-capable** — drives the actual bug path and asserts the user's exact symptom
- [ ] **Deterministic** — same verdict every run
- [ ] **Fast** — seconds, not minutes
- [ ] **Agent-runnable** — no human in the loop required

Build it first, run it, confirm it goes red. Only then continue to steps 1–5.

If you catch yourself reading code to build a theory before this command exists and has been run, **stop**. No red-capable command, no Phase 1 continuation.

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Weakest precondition (Huth & Ryan, Ch 4.3).** When the failing function has a
clear postcondition `Q` that did not hold, compute the weakest precondition of the
body *backwards* from `Q` (assignment = substitute `E` for `x` in `Q`; `if` =
`(B → WP_then) ∧ (¬B → WP_else)`; sequence = push `Q` through the last command
first). The WP is the *minimal* entry condition under which `Q` would hold. The
bug manifests exactly where the actual precondition does not imply that WP — that
gap is the reproduction case. Walk backwards until `actual P ⊨ WP` breaks; the
first broken command is the fault. Do not invent a forward story until this
backward scan has a concrete failing substitution.

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

### 4. Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (API → service → database, CI → build → deploy):**

Special case: monorepos and npm workspaces.
- Treat the package manager working directory as part of the system boundary.
- Reproduce both the wrapper path and the direct package path.
- Compare workspace-root install/build vs package-local install/build before changing code.
- If the direct package build works but the wrapper fails, isolate whether the wrapper is pulling unrelated workspaces, native deps, or extra lifecycle scripts.
- Fix the launcher/build context first; do not mislabel a package-local success as a frontend failure.

Special case: desktop/session-manager handoffs (GDM/Wayland/systemd --user/portals).
- Treat the display manager, the previous desktop session, `graphical-session.target`, and portal/user units as separate components with ordering edges between them.
- Collect previous-boot and current-boot journal windows around the exact login/logout timestamps before editing compositor config.
- Check whether the new session is racing shutdown of the previous one; a compositor crash can actually be a session deadlock during handoff.
- If logs show `xdg-desktop-portal.service` failing with `result='dependency'` while `graphical-session.target` is inactive, do not force-start the portal earlier from compositor startup config; fix the session-target ordering first.
- Prefer the smallest reversible startup nudge, then re-test with a clean reboot directly into the target session rather than bouncing through another desktop first.

Special case: unexpected Linux reboot/reset with no obvious panic.
- Treat kernel crash paths, system update automation, and user-level login services as separate components to isolate.
- After checking for panic/watchdog/thermal/MCE evidence, inspect `journalctl --user -b -1` for user services that ran shortly before the reboot.
- On OSTree/Silverblue systems, correlate `rpm-ostree`/`ostree` activity with local updater scripts before calling the event a hardware or kernel failure.
- Search local automation (`~/.config/systemd/user/`, `~/.local/bin/`, `~/.hermes/scripts/`) for explicit reboot commands; an update service may have rebooted intentionally.
- If a reboot command, staged deployment, and clean lack of crash signatures line up in time, classify it as automation-triggered until evidence shows otherwise.

Special case: Electron/Obsidian-style desktop apps that "don't work properly anymore" after updates or plugin drift.
- Treat the app core, workspace/layout state, and community plugins as separate components.
- Read the app logs and enabled-plugin manifest first, but do not wait for explicit stack traces; plugin breakage often fails "soft" with poor logs.
- Before broader resets, make timestamped backups of the plugin enablement file and workspace/layout file.
- Use the smallest reversible isolation step first: temporarily disable all community plugins by replacing the enabled-plugin list with `[]`, then restart and retest.
- If that restores the app, re-enable plugins in small batches or one-by-one to find the culprit; only reset workspace/layout state after the no-plugin baseline is known.
- Keep the backup paths in your final report so the user can roll back quickly.
- See `references/obsidian-plugin-triage.md` for a compact recovery sequence.

Special case: web data feeds that expose structured HTML when JSON/API routes fail.
- Reproduce both the API endpoint and the rendered page before changing downstream consumers.
- Inspect the rendered HTML for stable machine-readable attributes/tags before falling back to brittle text scraping.
- If one source branch succeeds and another fails, preserve the successful branch and surface a source-specific error instead of failing the whole report.
- See `references/web-feed-html-fallback.md` for a compact example of the Reddit/X-style fallback pattern.

Special case: refreshable recommendation UIs that "stop working" after several save/rate actions.
- Treat the browser control, the refresh endpoint, and the recommendation-pool/state rules as separate components.
- Reproduce both full refresh and the incremental save/rate -> refill path; a UI bug report can actually be an exhausted backend pool returning `[]`.
- Inspect whether saved/seen-state exclusion is permanent. If previously rated items are excluded forever, repeated use can make refresh appear broken even when the button and fetch logic still work.
- Verify the live API payload shape and count after several interactions, not just the page shell or a health endpoint.
- When exhaustion is valid, prefer a deliberate fallback policy over returning an empty list silently. Good options include: unseen-first from the curated shortlist, then backfill from a broader local seed catalog/library-derived pool that still respects the user's rated/seen exclusions; only revisit previously rated items if the product explicitly wants that and labels it clearly.
- If you introduce a fallback pool, verify the full write path too — not just the read/display path. In recommendation UIs with rating/save actions, newly surfaced fallback item IDs often fail later because the persistence path only knows about the original curated pool. Confirm that save/rate handlers can resolve and store fallback items without `unknown item`-style failures.
- See `references/recommendation-pool-exhaustion.md` for the compact reproduction and fallback pattern.

Special case: concurrent/async bugs and state explosion (Huth & Ryan, Ch 3.6).
- Model checking is linear in `|states| · |φ|`, but `|states|` is exponential in
  variables and parallel components. Adding one boolean *doubles* the space.
- Before scaling the debugger (more threads, longer stress, full product config),
  enumerate reachable states of a *small* explicit model (few flags, two workers,
  tiny queues). If that model already explodes, the concurrency design is too
  complex — simplify the protocol (fewer shared variables, coarser locks, less
  nondeterminism) before hunting the bug.
- Distinguish safety failures (finite bad interleaving: race, broken mutex) from
  liveness failures (infinite postponement: deadlock, starvation). The latter need
  a fairness assumption; spinning on a longer timeout is not a model.

**BEFORE proposing fixes, add diagnostic instrumentation:**

For EACH component boundary:
- Log what data enters the component
- Log what data exits the component
- Verify environment/config propagation
- Check state at each layer

Run once to gather evidence showing WHERE it breaks.
THEN analyze evidence to identify the failing component.
THEN investigate that specific component.

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### 6. Performance: recurrences before the profiler (CLRS 4th ed, Ch 4)

When the bug is slowness in **recursive** (or divide-and-conquer) code, do not start with a profiler.

1. Write the recurrence T(n) for the implementation as it actually recurses (number of subproblems a, subproblem size n/b or n−1, driving work f(n)).
2. If it is a master recurrence T(n) = a T(n/b) + f(n), apply the **Master theorem** (§4.5, Theorem 4.1): compare f(n) to the watershed n^{log_b a}. Case 1 leaves dominate; case 2 levels are equal (usual merge-sort Θ(n lg n)); case 3 root dominates — need polynomial separation and the regularity condition.
3. If it is not a master recurrence, use substitution (§4.3) or a recursion tree (§4.4). Classic trap: T(n) = 2T(n−1)+Θ(1) is exponential; no constant-factor tweak of the base case will save it.
4. Only after the Θ-class is known, profile for constants, cache, and implementation bugs that disagree with the model.

A profiler on n=20 of an exponential recursion reports "the base case is hot." The recurrence already said the algorithm is the defect.

<!-- why: CLRS Ch 4 solves divide-and-conquer cost from the recurrence; Master theorem is the cookbook before measurement. -->

### Phase 1 Completion Checklist

- [ ] **Tight feedback loop exists** — one command, already run, red-capable, deterministic, fast
- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

### 5. Expected steps when bisecting

When bisecting (`git bisect` or binary-search debugging), the expected number of
steps is log₂(N) — this follows from Shannon's binary decision argument: each
midpoint split yields exactly 1 bit of information, so N candidates need exactly
log₂(N) bits to resolve. If you are taking more steps, you are not bisecting —
you are exploring, which is less efficient.

Wald's **expected sample number (ASN)** is the complementary concept: the SPRT
achieves the minimum expected sample count when testing hypotheses sequentially.
Both converge on the same insight — efficiency is measured by E(n), not worst
case. A search with mean ≫ log₂(N) is not an optimal bisection procedure.
Return to a true midpoint split (or an SPRT-style stop when the likelihood ratio
has already crossed the threshold). See `wald-sequential-analysis`.

<!-- why: log2(N) for bisection is Shannon information; Wald ASN is distinct (SPRT) but the efficiency lesson is the same. Attribution corrected. -->
<!-- why: Wald ASN: efficiency is E(n); extra steps past log2 N mean the procedure is not the optimal sequential search -->

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 0. Reasoning gate — causal-check + hypothesize

Before forming any hypothesis, run the reasoning-framework gates:

  a. Distinguish cause from correlation (causal-check):
     ```
     python3 ~/.hermes/scripts/metacognitive-harness.py causal-check \
       --observation "<observed symptoms>" --candidate-cause "<suspected cause>"
     ```
     Exit 0 (CAUSAL): proceed with causal hypothesis. Exit 1 (CORRELATED): do not assert causation.
     Exit 2 (UNKNOWN): rule out this evidence path.

  b. Rank competing explanations (hypothesize):
     ```
     python3 ~/.hermes/scripts/critique-bank.py hypothesize \
       --observation "<symptom>" --context "<evidence so far>" \
       --candidates '["<h1>","<h2>","<h3>"]'
     ```
     Test only the top-ranked hypothesis first.

  c. Check for false attribution before reporting a fix:
     ```
     python3 ~/.hermes/scripts/critique-bank.py false-attribution \
       --claim "<X caused Y>" --context "<evidence so far>"
     ```
     HIGH risk = drop the hypothesis and re-rank.

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

### 5. Causal structure (Pearl)

### 4.5 Recursive functions — structural induction (Thompson)

**WHEN the failing code is recursive** (lists, trees, nested JSON, descent over
ASTs, `n`/`n-1` numeric recursion):

Apply structural induction mentally before tracing randomly:
1. **Base case** — does P hold on the constructors with no recursive arguments
   (`[]`, `0`, leaf, `Null`)?
2. **Inductive step** — assuming P on immediate predecessors, does P hold on the
   constructor that combines them?

A recursive bug lives in exactly one of these two places. If the base is wrong,
the whole recursion is wrong; if the step is wrong, a single constructor case is
wrong and the base may still be fine. Do not patch both at once. Recursion that
is not structurally decreasing (argument not a subterm) is a totality defect, not
an off-by-one — check termination separately. <!-- why: prevents shotgun edits across a recursive function when the failure is only base or only step -->

Correlation in logs or a green test is not a cause. Apply these before declaring root cause or victory.

**Confounding.** When a fix appears to resolve a bug in testing but fails in production, suspect a confounder — an unobserved variable correlated with both the fix-context and the outcome. Do not declare victory until the causal path is confirmed (not just correlated).
<!-- why: prevents treating a test-env correlation as the production cause -->

**Intervention vs observation.** Observing that X correlates with the bug is not the same as intervening on X. Distinguish "X appears when the bug appears" (observation) from "disabling X prevents the bug" (intervention). Only interventions confirm causation.
<!-- why: prevents promoting a co-occurring symptom to root cause -->

**Collider bias.** Conditioning on a collider (e.g. filtering logs to only error states) opens spurious correlations between independent causes. Log sampling and error-only analysis can manufacture false causal links. Analyze the unfiltered path, or sample successes as well as failures.
<!-- why: prevents false causal links from error-only log slices -->

### 6. Non-converging agent / value loops (Puterman)

When an iterative agent loop, planner, or RL backup **does not converge**, do not treat
"needs more iterations" or "tune the step size" as the first hypothesis. Bellman backups
have no step size. Distinguish the algorithm and the discount (see `puterman-mdp`):

- **Value iteration** (`v ← T v`) converges geometrically iff the discount γ (Puterman: λ)
  satisfies **γ < 1** on a discounted MDP. If γ ≥ 1, VI may oscillate; that is a
  well-posedness failure, not a coding glitch. Average-reward VI also needs extra
  structure (unichain, aperiodicity transform).
- **Policy iteration** (evaluate → greedy improve) **terminates in finitely many steps**
  at an optimum for finite state/action discounted MDPs. If PI is not terminating, the
  model is not a finite discounted MDP, evaluation is approximate/noisy, or improvement
  is not actually greedy.
- **First check:** is γ strictly less than 1? If not, convergence is not guaranteed.
  Then check: are you running VI or PI? Then check: is the "state" Markov, or is
  unbounded history making the backup ill-defined?

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

**Also re-run the Phase 1 feedback loop against the original scenario to confirm the symptom is gone** — not just that the regression test passes.

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If >= 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

**Retry classification before re-running (arXiv:2608.23610 — Retry Amplification):**
Naive retries under correlated failure reduce success from 55.4% to 41.5% vs no-retry.
Before re-running a failing test or re-deploying a fix, classify the failure:
- Transient (network timeout, I/O flake, race): retryable, max 2 retries with backoff.
- Deterministic (assertion failure, import error, type error, logic bug): NOT retryable.
  Running the same code against the same test again will fail the same way.
  Fix root cause before re-running. If >=3 distinct tests fail with different root
  causes simultaneously, treat as a correlated environment failure (fix the environment,
  not individual tests).

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

### 6. Cleanup Before Declaring Done

Once the fix is confirmed working (step 3 passes, Phase 1 loop goes green):

- [ ] Original repro no longer reproduces (Phase 1 loop confirmed green)
- [ ] Regression test passes
- [ ] All `[DEBUG-...]` tagged instrumentation removed (grep the prefix)
- [ ] Throwaway prototypes/harnesses deleted
- [ ] The hypothesis that turned out correct is stated in the commit message — so the next debugger learns

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Build feedback loop (red-capable command), read errors, reproduce, check changes, gather evidence, trace data flow | Tight loop exists and goes red; understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify loop goes green, cleanup | Bug resolved, all tests pass, loop green, no debug artifacts |

## Hermes Agent Integration

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`browser` tools** — Verify web-app fixes at the user-facing layer after process/log checks; use this when a server can be "up" while the UI is still broken
- **`web_search`/`web_extract`** — Research error messages, library docs

Reference: `references/web-monorepo-build-context.md` for the npm-workspace wrapper-vs-package debugging pattern.
Reference: `references/desktop-session-handoff-debugging.md` for GDM/Wayland/systemd-user/portal race investigations.
Reference: `references/linux-unexpected-reboot-investigation.md` for distinguishing crash/reset events from intentional update-triggered reboots on Linux hosts.
Reference: `references/obsidian-plugin-triage.md` for the safe backup → disable-all-plugins → retest sequence before workspace resets in Obsidian-style desktop apps.
Reference: `references/recommendation-pool-exhaustion.md` for dashboards where repeated ratings/save actions exhaust the unseen pool and make refresh look broken.
Reference: `references/sqlite-wal-generation-debugging.md` for the SQLite WAL-generation / `DeletedWalGenerationError` diagnostic and fix sequence (compile-time vs runtime version mismatch, deleted-inode FD scan, artifact change_counter check, `journal_mode: delete` fix).

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression

## ML test-vs-production dimensionality mismatch (Hastie ESL Ch 2.5)
**Symptom:** Model (or ML pipeline) looks good in tests / CI fixtures, fails in production.
**Hypothesis to check before rewriting the model:** dimensionality mismatch. Test data is often low-dimensional, dense, and typical; production data is often high-p, sparse, or on the boundary of the training support. Sampling density scales as N^{1/p}; local methods and overfit low-p fixtures do not transfer. This is a distribution / support problem (curse of dimensionality), not necessarily a code defect.
**Debug:** compare p, sparsity, and feature-support overlap between the test fixture and a production sample *before* changing architecture or hyperparameters. If production p ≫ test p, the test never exercised the failure mode.

## Web monorepo build-context mismatch
**Symptom:** Wrapper/launcher says `npm install failed` or `build failed`; manual `cd <package> && npm install && npm run build` succeeds.
**Root cause:** Repo moved to npm workspaces but launcher still runs from workspace root with a different working directory or installs in isolation.
**Debug:** Reproduce wrapper path exactly → reproduce direct path exactly → compare working directories → check whether workspace-root install propagates to the package.

## Desktop session handoff debugging (Wayland/GDM)
**Symptom:** Compositor session fails after login (black screen, immediate crash), sparse output.
**Hidden cause:** Previous desktop session shutdown overlaps new session startup.
**Evidence:** `gdm-wayland-session` aborts with `std::system_error`; `graphical-session.target` becomes inactive during startup; `xdg-desktop-portal.service` dies.
**Fix:** `journalctl -b -1 -u gdm -u graphical-session.target --no-pager | tail -50` from prev boot; look for shutdown/startup race. Adding `ExecStartPre=sleep 1` to the compositor unit often resolves it.

## Linux unexpected reboot investigation (fast triage)
1. Anchor timeline: `who -b`, `last -x`, `journalctl --list-boots`
2. Check prev boot for crash: kernel panic/BUG/Call Trace, watchdog, thermal, MCE, OOM
3. If no crash: look at systemd user services started near login (reboot loop), manual `shutdown`/`reboot` in bash history, `journalctl -b -1 -p err -x`
4. If thermal: `sensors` + `journalctl -b -1 | grep -i 'thermal\|temperature\|overheat'`

## Web feed HTML fallback for blocked JSON/API endpoints
When a JSON endpoint returns 4xx/5xx intermittently but the rendered page still has structured data:
- Reddit: `<shreddit-post>` elements carry `post-title`, `permalink`, `score`, `comment-count` attributes even when JSON API is blocked
- Pattern: try JSON endpoint → on failure, fetch HTML → parse structured attributes with BeautifulSoup
- Key: `requests.get(url, headers={'User-Agent': 'Mozilla/5.0 ...'})` to avoid bot blocks on HTML fallback

## Optimizer not converging or oscillating (Boyd & Vandenberghe)

**Symptom:** Custom optimizer / GD / Newton diverges, oscillates, crawls, or "objective decreased" but the iterate is not a solution.

**Do not retune blindly.** These are the three failure modes; check in this order (load `boyd-convex-optimization`):

1. **Is the objective actually convex on the domain being used?** Second derivative `≥ 0` or Hessian PSD. A convex solver on a nonconvex objective has no global guarantee; this is a correctness bug, not a step-size bug.
2. **Is the step size too large?** Fixed-step GD requires `t ≤ 1/L` (`L` = Lipschitz constant of `∇f`, equivalently Hessian bound `M`). `t > 1/L` typically oscillates or diverges. If `L` is unknown, switch to backtracking; if `f` is infinite outside `dom f`, pull `t` onto the domain first (NaN/Inf in `f` or `∇f` is usually this).
3. **Conditioning?** Ill-conditioned Hessian (`M/m` large) yields a slow linear rate even with a correct step — long thin sublevel sets, zigzagging GD. Check Hessian eigenvalues / feature scales. Fix scaling or switch to Newton (Cholesky on `H Δx = -g`) / a preconditioned method.

**Certificate vs symptom:** a decreasing objective is not evidence of optimality. Unconstrained: `∥∇f∥` (or Newton decrement `λ²/2`) must be small. Constrained: duality gap and KKT residuals must be small.

## Research Provenance

## Recommendation/refreshable surface pool exhaustion

**Symptom:** Dashboard or recommendation panel stops refreshing after repeated save/rate actions.
Refresh button appears dead or returns the same empty state. Health checks still pass (so app
looks "up" while the recommendation surface is broken).

**Root cause:** Backend permanently excludes all previously rated/seen items. After enough
interactions, the unseen pool is exhausted — the endpoint returns an empty array. Frontend is
fine; it just has nothing left to render.

**Debug steps:**
1. Hit the refresh/recommendation endpoint directly, record the recommendation count.
2. Check if count drops to 0 (pool exhausted) vs returning an error.
3. Inspect backend exclusion logic — look for a `seen_ids` or `rated_ids` filter.

**Fix options:**
- Add a `reset_seen` mechanism or TTL on the exclusion set.
- Cap the exclusion list to a rolling window (last N items).
- Fallback: re-surface old items when pool < N.
- Surface pool size in the health endpoint so depletion is visible before the UI breaks.

## CFA — Causal Failure Attribution for Multi-Step Agent Pipelines (arXiv:2608.20627, Aug 2026) <!-- rationale: when multiple pipeline stages could have caused a failure, counterfactual substitution isolates the root cause without re-running the full pipeline -->

**Problem:** In multi-stage agent pipelines (retrieve → filter → synthesize → generate), a failure
in the final output could have originated at any stage. Standard debugging re-runs the full
pipeline, which is slow and doesn't isolate the cause.

**CFA method (counterfactual substitution):**
1. Identify each pipeline stage and its output
2. Replace each stage's output with a "gold" (known-correct) value, one stage at a time
3. For each substitution: does the downstream failure resolve?
4. The first substitution that resolves the failure isolates the faulty stage

```
Pipeline: retrieve(query) → filter(results) → synthesize(filtered) → answer(synthesis)

Failure observed at: answer

Test 1: replace synthesize output with gold synthesis → answer still fails → synthesize is NOT the root cause
Test 2: replace filter output with gold filter → failure resolves → filter is the root cause
```

**Hermes implementation for agentic pipeline debugging:**

When a multi-step agent task fails and you can't identify the stage from logs alone:
1. Enumerate all stages as: `[tool_call_1 → tool_call_2 → ... → tool_call_N]`
2. For each stage from N-1 down to 1:
   - Re-run the downstream stages using the CORRECT output for stage K (what the output SHOULD have been)
   - If the failure resolves: stage K was the root cause
3. Apply the standard 4-phase debugging protocol to stage K specifically

**When CFA replaces standard debugging:**
- Use CFA when: failure is in stage N but you suspect the bug is in stage 1..N-1
- Use CFA when: re-running the full pipeline is expensive or has side effects
- CFA is most useful when intermediate outputs can be saved and replayed (use Hindsight to record stage outputs for debugging sessions)

**Integration with existing debugging phases:**
- CFA replaces Phase 1 "Trace Data Flow" step (§5) for multi-stage pipelines — it's faster than manually tracing data through each stage
- Once CFA identifies the faulty stage, enter Phase 2 (Pattern Analysis) on that stage specifically
- CFA is the evidence-gathering method; the 4 phases are still the fix cycle

**Pitfall:** CFA requires knowing what the "gold" output for each stage should be. For research pipelines (web_search → filter → synthesize), the gold is the FULL, UNFILTERED search results before any stage-specific processing. Don't substitute with a fabricated gold — use a known-good real example.

Reference: arXiv:2608.20627, "When Failures Propagate: Causal Failure Attribution in Agentic Retrieval Pipelines", Aug 2026.

### 10-Category Agent Failure Taxonomy (arXiv:2608.09939)
Empirical study classifying autonomous agent failures into 10 categories with frequency data:
1. Tool hallucination (28%) — agent calls tool with fabricated args or nonexistent tool name
2. Context truncation (21%) — critical context falls outside window; agent proceeds on partial data
3. Goal drift (18%) — subgoal optimization diverges from original goal
4. Over-delegation (12%) — subtask spawned unnecessarily, adding latency and error surface
5. Under-delegation (9%) — complex subtask handled inline when subagent would be safer
6. Loop stall (6%) — agent repeats same action with no progress, no exit condition
7. Permission error (3%) — tool call refused; agent neither retries nor escalates
8. Partial success treated as complete (1.5%) — absence of explicit error treated as success
9. Cascade failure (1%) — single tool error propagates to corrupt subsequent tool inputs
10. State corruption (0.5%) — shared state written incorrectly; later reads get wrong values
**Hermes application:** When debugging an agent failure, classify it into the taxonomy first.
The category determines the fix strategy: hallucination → add verification step; truncation →
reduce context or switch to session_search; goal drift → add goal-check sentinel every N steps.

### Dependency-Guided Rollback for Memory Errors (arXiv:2608.10502, Sweep 12)

Persistent memory errors are durable: a poisoned/stale/misattributed record alters reasoning,
tool use, answers, AND subsequent memory writes. Standard defenses either delete the source
(leaving propagated claims active) or replay the full trace (destroying benign state).

Key finding: 85.3% recovery rate using typed memory-to-action graph with selective replay vs
77.3% for best competitor; 0% faulty memory leakage.

**Hermes debugging protocol when a memory error is suspected:**
1. Identify the suspect memory fact (Hindsight/MEMORY.md/Graphiti entry)
2. Trace which actions/decisions used that fact in this and prior sessions (provenance audit)
3. For each downstream action: was the outcome affected by the faulty fact?
4. Selectively re-run only the affected computations with the corrected fact
5. Do NOT wipe the entire session or full Hindsight bank — surgical replay only

**Practical provenance log (add this discipline to long agentic runs):**
When acting on a retrieved memory: note `[used: <entry_id>/<source>]` in reasoning.
When invalidating a memory: search for that note pattern to find downstream uses.

**Root cause signal:** if multiple unrelated actions in a session are producing wrong results
simultaneously, suspect a shared memory dependency rather than individual tool errors.
See 10-Category Agent Failure Taxonomy above for the full classification (Tool hallucination → hallucination → add verification step, etc.).



From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**

## Theory-Grounded Root Cause Analysis

### Probability of Causation: PN, PS, PNS (Pearl Ch 9)

**Theory:** For a candidate cause X and outcome Y:
- PN (Probability of Necessity) = P(Y=0 | do(X=0), Y=1, X=1) — would the bug be absent if we removed the cause?
- PS (Probability of Sufficiency) = P(Y=1 | do(X=1), Y=0, X=0) — would the cause alone produce the bug?
- High PN AND high PS → genuine root cause. Low PN → confounded (another cause also present).

**Hermes rules:**
- Before fixing a bug, estimate PN and PS qualitatively: "If I remove this change, does the bug disappear? (PN). If I apply this change on a clean system, does the bug appear? (PS)."
- If both are high: fix this cause. If PN is low: the bug has other contributing causes — investigate them before fixing.
- Do NOT fix the most visible cause without checking PN; confounded fixes produce regression without resolution.

**Citation:** Judea Pearl — *Causality* (2nd ed.), Ch 9 (Probability of Causation).

### Preemption and Overdetermination (Pearl Ch 10)

**Theory:** Overdetermination: multiple causes independently sufficient for the same effect. Preemption: one cause fires before another and "takes credit" for the effect, even though both would have caused it.

**Hermes rules:**
- When multiple potential causes are present simultaneously, treat each independently with a counterfactual test (do-calculus): "If I remove only cause A (holding B constant), does the bug persist?"
- Do NOT assume the first cause identified is primary without counterfactual check — it may be preempting a deeper cause.
- Overdetermined bugs (two independent causes both producing the same failure) require fixing both; fixing one may appear to resolve the issue but the other cause remains latent.

**Citation:** Judea Pearl — *Causality* (2nd ed.), Ch 10 (The Actual Cause).
