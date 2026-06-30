---
name: review-driven-followup-fixes
description: "Handle follow-up passes on reviewed code changes: mine reviewer signal, inspect nearby risks, verify surgically, and commit only after fresh evidence."
---

# Review-Driven Follow-Up Fixes

Use this when a user asks for another pass after PR feedback, review comments, or a recently landed fix. This skill is for the class of work where the first fix may be correct but incomplete, and the real job is to close the nearby gaps without widening scope.

## Triggers
- "Do another pass"
- "Check the PR comments and fix everything relevant"
- "Review the follow-up feedback and push a cleanup"
- A prior fix already landed, but the user wants one more inspection/fix/verify/commit/push cycle

## Goals
1. Extract the real reviewer signal, including stale or merged-PR edge cases.
2. Inspect the touched surface for adjacent UX, accessibility, and error-handling gaps.
3. Make the smallest fix that resolves the issue cleanly.
4. Re-run focused verification and repo preflight before commit/push.

## Workflow
1. Establish branch reality first.
   - Check branch status, upstream, and whether the working tree is clean.
   - Determine whether the referenced PR is still open, merged, or otherwise stale.

2. Mine reviewer signal from multiple surfaces.
   - Check normal PR comments.
   - Check review threads / review comments separately.
   - If the PR is merged or stale and thread APIs are empty, do not stop there: inspect the active branch and recent touched files directly. Historical PR state may no longer reflect the actionable branch state.

3. Constrain the search to the touched area.
   - Read the changed files and nearby tests.
   - Search for adjacent controls, duplicated UI affordances, missing failure states, and nearby a11y gaps.
   - Prefer one additional targeted pass over a broad refactor.

4. When adding user-visible failure handling, prefer upgrading the existing surface.
   - If an error already renders in the active view, improve that surface (for example by adding accessible semantics like role="alert") instead of adding a second error block elsewhere.
   - Clear stale errors before a new action that can fail.
   - For popup/open-in-new-tab flows, treat a null return from window.open(...) as a blocked popup and surface a clear user-facing message.

5. Verify narrowly, then verify repo-wide gates.
   - Re-run the most relevant targeted tests for the touched file(s).
   - Re-run typecheck/build checks that cover the changed surface.
   - Run the repo's preflight / hygiene checks before commit.
   - If an attempted test assertion fails because the UI now renders duplicate matching text, inspect the DOM before retrying; the fix may be duplicate rendering rather than a bad test.

6. Commit and push only after fresh evidence.
   - Stage only the intended files.
   - Use a commit message that describes the follow-up fix, not the investigation.
   - Push and then verify branch/head state.

## Pitfalls
- Do not assume an empty review-thread API means there is no remaining work; merged PRs often require branch-based follow-up inspection.
- Do not add a new alert container if the same error is already shown elsewhere in the current view; convert the existing surface into the accessible/clear one.
- Do not rely on historical PR metadata alone when the branch has moved beyond the PR head.
- Do not stop after the first fix; do one deliberate adjacent-risk pass for UX/a11y/error handling around the touched code.

## Verification Checklist
- Reviewer signal checked from more than one PR/comment surface when applicable
- Nearby changed UI manually inspected via code/tests
- Failure path covered by a targeted test
- Existing error surface used without duplicate messaging
- Focused tests pass
- Typecheck/build checks pass
- Preflight/hygiene checks pass
- Commit created and push verified

## References
- Add session-specific notes under `references/` when a repo exposes unusual PR/comment behavior or a recurring verification quirk.
