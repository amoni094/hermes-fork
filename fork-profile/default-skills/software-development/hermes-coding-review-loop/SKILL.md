---
author: Hermes Agent
depends_on: [requesting-code-review, test-driven-development, systematic-debugging]
provides: [iterative-review, bounded-code-iteration, review-gates]
description: 'Use when: making code changes and wanting review gates at each iteration. Iterative inspect-edit-verify-review
  loop for bounded code changes with minimal diffs and explicit validation.'
license: MIT
metadata:
  hermes:
    related_skills:
    - hermes-agent
    - test-driven-development
    - requesting-code-review
    - systematic-debugging
    - hermes-operating-pattern
    tags:
    - hermes
    - coding
    - review
    - verification
    - diffs
    - tests
name: hermes-coding-review-loop
related_skills:
  - hermes-agent
  - test-driven-development
  - requesting-code-review
  - systematic-debugging
  - hermes-operating-pattern

triggers:
- making bounded code changes and wanting automated review gates after each iteration
- running an iterative patch-and-review loop on a specific file or module
- user wants code review applied automatically during implementation, not just at the end
- need to keep diffs minimal and verifiable across a series of edits
- want a repeatable inspect-edit-verify cycle with explicit validation steps
version: 1.0.0
---


# Hermes Coding and Review Loop

## Overview

Use this skill for bounded implementation work where correctness matters more than speed alone.

The loop is: inspect the relevant files, make the smallest useful patch, run the local checks that match the change, fix what verification reveals, and only then report the result.

## When to Use

- You are editing code in a repository.
- You need to keep diffs minimal and understandable.
- You want a repeatable review loop that does not rely on vague judgment.
- You need to convert review feedback into durable changes.

## Review Loop

For each review pass, apply boundary-check before marking items resolved:
  ```
  python3 ~/.hermes/scripts/metacognitive-harness.py boundary-check \
    --task "<review item>" --action "<fix applied>"
  ```
  Exit 1 (INCOMPLETE), exit 2 (OVER_ACTION), or exit 3 (SCOPE_CREEP): do not mark resolved.

For regression attribution ("did fix X resolve test failure Y"), run causal-check:
  ```
  python3 ~/.hermes/scripts/metacognitive-harness.py causal-check \
    --observation "failure Y resolved" --candidate-cause "fix X" \
    --evidence "<test output delta>"
  ```
  Exit 1 (CORRELATED): do not claim the fix caused the pass; investigate further.

1. **Run `diff-impact.py`** to estimate blast radius and confidence. Load the suggested skill hooks.
2. Inspect the target files and nearby context.
3. Make the smallest patch that solves the problem.
4. Run the relevant tests, lint, format, or validation steps.
5. Fix issues that the verification reveals.
6. Repeat until the result is clean.
7. **Skill-freshness check:** before closing, ask whether this diff invalidates or should update any Hermes skills — did an API, CLI, file layout, or workflow change that a skill documents? If yes, patch that skill in the same commit or flag it as a follow-up. Skills are procedural memory; silently obsoleting one is knowledge-rot.
8. Record the durable lesson in docs or notes.

## Practical Rules

- Prefer a narrow patch over a broad rewrite.
- Avoid blind search-and-replace unless the match is clearly safe.
- Keep symbols and blast radius in mind before changing shared code.
- Use structured outputs and explicit checks when the result will be reused.
- Treat “looks good” as insufficient without a real check.
- When reviewing an external guide or optimization repo against the current codebase, first separate real product gaps from discoverability gaps. If the feature already exists, prefer tightening help text, docstrings, prompt-size labels, or tool-schema descriptions over inventing a larger implementation.
- For small doc/help patches that touch executable Python modules, verify cheaply but explicitly: run the narrow pytest slice that exercises the changed surface and a syntax pass such as `python -m py_compile` on every edited file.
- If a patch tool corrupts a long string or nested literal, inspect the exact damaged region and repair it with the narrowest possible replacement before continuing. Do not trust a successful partial patch when lint or syntax checks disagree.

## External Guide Audit Pattern

Use this pattern when a repo, blog post, or optimization guide claims there are improvements to make:

1. Read the guide and extract concrete claims, not just vibes.
2. Compare each claim against the current checkout.
3. Mark each item as one of:
   - already implemented,
   - implemented but under-documented or hard to discover,
   - genuinely missing.
4. Implement the smallest real improvement that closes the gap.
5. Add or update a targeted regression test for the user-facing behavior you changed.
6. Run lightweight verification before reporting success.

See `references/external-guide-audit.md` for a compact worked pattern.

## External Guide Audit Pattern (from external-guide-audit.md)

When a user points Hermes at an external optimization guide/workflow repo and asks whether anything should change locally — turn the guide into a grounded audit of the current checkout, not cargo-culting.

**Fast classification for each recommendation:**
1. **Already implemented** — no code change needed.
2. **Implemented but hidden** — improve discoverability: CLI help, tool descriptions, docs, prompt labels, or tests. This bucket matters — many useful improvements are discoverability fixes, not architecture work.
3. **Actually missing** — implement the smallest useful change.

**Verification recipe for small Python help/doc patches:**
1. Add a targeted pytest file that checks the exact help text / schema description / exported label.
2. Run with repo addopts disabled if optional plugins are missing: `PYTHONPATH=. ~/.local/bin/pytest tests/cli/test_context_file_help_text.py -q -o addopts=''`
3. `python3 -m py_compile <edited-files>` on every edited Python file.

**Patch-tool pitfall:** Long JSON-schema description strings are easy to damage with automated patching. If lint reports syntax errors after a text-only change: inspect the exact literal, repair the smallest broken span, rerun syntax verification immediately. Do not stack edits on top of a malformed dict or string literal.

## ExecCritic Pattern (arXiv:2609.09133) — Frozen Tests + Separate Repair Agent

Same-trajectory test-and-patch creates false confidence (tests that pass because they were written by the same agent that broke the code). ExecCritic (arXiv:2609.09133 "Learn to Test, Test to Improve for Coding Agents") separates the test-writing and repair roles to break false-confidence loops.

**What the paper actually shows:** Holding Repair fixed, a naive untrained Test agent *lowers* resolve rate (61.2% → 57.3%). The 72.6% figure requires two role-specific RL post-trained agents (Qwen) that Hermes does not have. The value of this pattern for Hermes is **false-confidence prevention** — not a free 11.4pp gain.

**What you get without RL post-training:** A structurally cleaner separation that prevents the same agent from writing and evaluating its own tests. Expect little or no raw score improvement; expect better auditability.

**Phase 1 — Test Agent** (separate subagent or first pass before code touch)
- Writes and commits tests BEFORE seeing or touching any source change
- Tests must be runnable and fail red on the current (unmodified) codebase
- Commit hash of test suite is recorded as the frozen baseline

**Phase 2 — Test directory lock (prompt-level only)**
The test directory is marked read-only in the Repair Agent's context. This is a prompt constraint, not an enforced filesystem lock — tool-auth-gate.py is advisory and does not block writes. For a hard lock, use `git update-index --skip-worktree tests/` before the Repair Agent starts.

**Phase 3 — Repair Agent** (separate subagent or second pass)
- Edits source ONLY; touches no test files
- Succeeds when the frozen test suite passes green
- Adversarial reviewer (cold subagent, different model) evaluates the repair — never the Repair Agent itself

**ExecCritic violation (flag, do not accept):** If the Repair Agent modifies any test file (`tests/`, `*_test.py`, `test_*.py`, `*.spec.*`, or the frozen test-suite hash changes), flag as an **ExecCritic violation**. Restore tests from the frozen hash, reject the repair, and re-run Repair with tests locked. A green suite after the Repair Agent edited tests is false confidence — treat as fail.

**Hermes integration:**
```yaml
# In delegate_task context for Repair Agent:
"Test files at tests/ are frozen (hash: <sha>). Do not edit them.
tool-auth-gate is advisory and will not physically block writes;
for a hard lock use: git update-index --skip-worktree tests/
Your only success criterion: the frozen test suite passes."
```

**Pre-launch checklist addition:**
- [ ] For coding tasks: Test Agent committed before Repair Agent starts; test dir hash recorded
- [ ] Repair Agent context explicitly states test files are locked
- [ ] Adversarial reviewer is a cold subagent (different model family from Repair Agent)

**Pitfall:** Do NOT use the adversarial reviewer to generate tests — it must stay off the Repair path entirely. Reviewers that share the same spec as the implementation tend to find the same blind spots (agreement ≠ independence).

## Semantic Triangulation (arXiv:2511.12288)

Require **two independent** semantic checks before marking code as done:

1. **Automated tests pass**
2. **Spec replay** — re-read the original requirement and verify the code satisfies it **without looking at the tests**

Both checks must pass. A passing test suite alone is insufficient (tests may be wrong). Complements ExecCritic (frozen tests vs repair) — triangulation catches a green suite that does not match the spec.

## Role Drift Prevention in Coding Subagents

Source: arXiv:2609.03111 (Role Drift in Hierarchical MAS) — verifier-role agents drift
into proposing fixes; repairer agents drift into strategic refactors.

Every coding subagent goal must include an explicit role declaration:
- Reviewer: "Your role is REVIEWER. Flag issues and explain why. Do NOT propose replacement
  code or modify files."
- Repairer: "Your role is REPAIRER. Edit implementation files only. Do NOT modify test files
  or review criteria."

If a reviewer's output contains code blocks proposing direct replacements, treat as lower-trust
and route through a second cold reviewer before acting.

## LLM Observer Unreliability

Source: arXiv:2609.04198 — same-window LLM judge repeat rankings agree at Spearman 0.40,
far below the 0.90 required for a reliable gate.

Rule: LLM review is advisory, not a pass/fail scorer.
- Run deterministic gates first: linter, formatter, test suite pass/fail.
- Never use a single LLM review invocation as the sole quality gate.
- If multiple LLM reviewers are used, each must have cold context (no shared session history).
  Same-window repeated review degrades to near-random agreement.
- For any cron or automated pipeline using LLM self-scoring, switch to deterministic
  metrics or pin model + temperature=0.

## Retry Classification Before Re-running Tests

Source: arXiv:2608.23610 (Retry Amplification) — naive retries under correlated failure
reduce success from 55.4% to 41.5% vs no-retry.

Classify test failures before deciding to retry:
- Transient (network, I/O, timeout, flaky): retryable, max 2 retries.
- Deterministic (assertion failure, import error, type error): NOT retryable.
  Fix root cause before re-running. Never spin the same test with the same code.
- If >=3 tests fail with different root causes simultaneously: treat as correlated
  environment failure. Fix environment, not individual tests.

## Common Pitfalls

1. Editing before inspecting nearby context.
2. Shipping a patch without running the relevant checks.
3. Rewriting more than needed and increasing risk.
4. Reporting success before the change is verified.
5. Using a single LLM review as a binary gate (Spearman 0.40 — noise, not signal).
6. Allowing a repair agent to edit its own tests (ExecCritic violation).
7. Retrying deterministic failures without fixing root cause (amplifies failure rate).

## Verification Checklist

- [ ] Relevant files were inspected first.
- [ ] The patch is as small as practical.
- [ ] The right checks ran for the touched surface.
- [ ] Verification passed or failures were fixed.
- [ ] The durable lesson was recorded if the workflow will repeat.

## Turbo Decoding as Iterative Review Convergence (Gallager Ch 6)

**Theory:** Turbo codes use iterative decoding: two decoders pass "extrinsic information" (new findings not already known to the other) back and forth. Each pass refines the estimate of the correct codeword. Decoding converges when the extrinsic information exchange stops changing (no new findings per pass).

**Hermes rules:**
- Treat each code review pass as a turbo decoding iteration: the pass improves the estimate of the correct code by incorporating findings not seen in prior passes.
- Convergence criterion: terminate when new findings per pass < 1. If pass N finds no new defects that pass N-1 did not find, the review has converged — do not run more passes.
- Extrinsic information only: each pass should search for defects the prior pass missed, not re-examine already-resolved findings. Reviewing the same defect twice is convergence-zero (no new extrinsic information).

**Citation:** Robert G. Gallager — *Information Theory and Reliable Communication*, Ch 6 (Block Coding and Turbo Codes — iterative decoding).
