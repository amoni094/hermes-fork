---
name: scoped-pr-fix-and-verification
provides: [git_ops, shell_exec]
triggers:
  - An existing GitHub PR branch needs verification and fixes before merge
  - Repo has custom quality gates beyond a single test command
  - Need to separate branch regressions from baseline failures before committing
  - PR is failing CI and needs targeted fixes with branch-scoped diff verification
description: >
  Use when fixing a PR branch under repo-specific quality gates, separate branch regressions from baseline failures, then commit and push only verified scoped changes.
related_skills:
  - github-issue-to-pr
  - github-operations
  - split-ci-workflow-change-and-draft-pr
  - verification-before-completion
---

# Scoped PR fix and verification

Use this when the user asks you to take an existing PR branch, run repo preflight/checks, fix what is required, and commit/push without widening scope into unrelated baseline failures.

Repo-specific operating rules are part of the verification contract. If AGENTS.md or local repo policy requires extra gates such as custom preflight wrappers or code-intelligence checks (for example GitNexus impact/detect-changes), run them before commit/push when possible. If one of those mandatory checks crashes or cannot complete after a documented retry/recovery attempt, finish the remaining proof set and report the blocker explicitly rather than implying the check passed. See `references/dashboard-maker-followup.md` for a concrete pattern.

## When to use
- Existing GitHub PR branch already exists and needs verification/fixes.
- Repo has custom quality gates beyond a single test command.
- Full test suites may contain known or unrelated failures that are not caused by the branch.
- You need to commit only the verified branch-relevant fixes and avoid stray generated files.

## Core workflow
1. Load the repo branch exactly as reviewed.
   - Clone/fetch and check out the PR branch.
   - Read repo guidance first (`CLAUDE.md`, `AGENTS.md`, test docs, CI docs, deploy/preflight scripts).

2. Identify the review target before editing.
   - Pull PR metadata and review comments.
   - Fetch the PR head branch explicitly and compare local `HEAD` to `origin/<head-branch>` before assuming your checkout reflects the reviewed state.
   - If the PR is already merged or closed, do not treat `gh pr view` metadata as the source of truth for the branch tip; verify the live branch ref directly (`git fetch`, `git rev-parse origin/<head-branch>`, or `gh api repos/<owner>/<repo>/git/ref/heads/<head-branch>`), because historical PR `headRefOid`/review state may remain stale after later branch pushes.
   - Inspect the exact files/areas mentioned by the review or touched by the branch.
   - Check recent branch commits in case the branch already contains a partial fix.

3. Run cheap/high-signal gates first.
   - Repo-specific preflight/security scripts.
   - Lint/typecheck/route-sync/schema/compat checks.
   - If repo guidance mandates a code-intelligence or change-impact loop (for example GitNexus `impact` before edits and `detect-changes` before commit), run it as part of preflight/review rather than treating it as optional.
   - Capture the exact failing output before changing code.

4. Triage failures into two buckets.
   - Bucket A: branch-caused failures blocking this PR.
   - Bucket B: unrelated baseline failures already present elsewhere in the repo.
   - Do not assume a failing full-suite command means the branch is at fault.

5. Fix only Bucket A.
   - Prefer the smallest change that makes the branch correct.
   - If a build/generated file changes only because a tool ran, revert it unless the source change truly requires committing it.

6. Re-run verification in widening rings.
   - Re-run the originally failing cheap gates.
   - Run targeted tests covering touched files/behavior.
   - Run broader package-level tests/builds as far as they remain informative.
   - Re-run repo-mandated review/intelligence checks before commit/push (for example `detect-changes`-style affected-scope analysis) when the repo requires them.
   - Run an optional final QA pass with `toolbox run ouroboros qa` on the exact diff summary, PR draft, touched workflow file, or captured test output when a second-opinion read is useful.
   - If the local Ouroboros runtime is unauthenticated or unavailable, treat that as an optional QA skip and continue with the executable proof set.
   - If a repo-mandated verifier crashes or cannot complete, do not silently skip it: record the exact command and blocker, continue with the remaining independent proofs, and report that gap explicitly in the final handoff.
   - If unrelated baseline failures remain, explicitly separate them from the branch fixes in your report.
   - If a repo-level adversarial/preflight scan starts flagging many unrelated findings after merging the latest base into the PR branch, do not treat that alone as a failure of the scoped fix; verify the touched files with targeted tests and document the inherited wider-diff findings explicitly on the PR.

7. Commit only intended files.

   - Stage only the files that implement or verify the branch fix.
   - Leave unrelated untracked workspace files out of the commit.

8. Push and report clearly.
   - Push the branch.
   - Confirm the PR head SHA updated.
   - Re-query unresolved review threads/comments after the push.
   - If repo-wide preflight still reports inherited branch-wide findings, post a concise evidence-backed PR comment distinguishing those from the scoped fixes you verified.
   - Report: what changed, what passed, what remains unrelated, commit SHA, and branch name.

## Practical heuristics
- If a repo has custom gate scripts, trust them over generic assumptions.
- When the target PR is merged but the user still wants branch follow-up, work against the live branch, not the historical PR snapshot. Review comments can still describe relevant unfixed branch work even when the PR state is `MERGED` and `gh pr view` still reports an old head SHA.
- When a global suite fails, find one or more targeted suites that directly exercise the touched behavior.
- If you extend a backend handler payload or persistence shape, add or update a targeted handler test in the same pass so the new contract is asserted where it is serialized.
- For backend handler tests that inspect S3/Dynamo writes, reset or replace shared mocks inside the specific test before asserting persisted payloads; otherwise earlier test fixtures can make a good handler change look like a 500.
- After a large frontend component rewrite, run a real production build even if unit tests pass; design-token/type mismatches often surface only during framework typecheck/build.
- Treat environment/setup import errors as separate from branch regressions unless the branch changed dependency declarations or test wiring.
- Prefer reverting build-only/generated edits (for example framework-generated type files) if the source fix does not require committing them.
- If upstream tracking/ref discovery is inconsistent, verify branch state with `git status -sb`/`branch -vv`; a failed explicit `fetch origin <branch>` does not by itself block committing and pushing `HEAD:branch` once the local branch is verified.

## Pitfalls
- Don’t widen scope by fixing every unrelated failing test in the repository.
- Don’t commit generated files just because a build or typecheck touched them.
- Don’t stop after one green command if the repo’s documented gates require more.
- Don’t silently omit a repo-required analysis tool just because your normal test/lint loop passed; either run it or explicitly report why it could not be completed.
- Don’t claim “all tests pass” when only targeted or informative subsets are green.
- Don’t push with unrelated untracked local artifacts staged by accident.

## Verification checklist
- PR branch checked out and repo guidance read.
- Repo-specific preflight scripts run.
- Originally failing branch-relevant gates now pass.
- Targeted tests for touched behavior pass.
- Build/typecheck rerun if frontend/app routing changed.
- `git diff` reviewed for unintended/generated changes.
- Commit contains only scoped verified files.
- Push succeeded.

## Linked references
- `references/scope-and-baseline-triage.md` — notes on separating branch regressions from baseline failures and keeping commits clean.
