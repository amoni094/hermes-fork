# Clean follow-up PR branching

Use this when a follow-up fix was made after the original feature PR already merged, and the old branch now carries historical commits that would pollute a new PR.

## Detection

Run before opening the follow-up PR:

- `git fetch origin main`
- `git diff --stat origin/main...HEAD`
- `git log --oneline origin/main..HEAD`
- optional: `gh pr diff <pr-number> --name-only` or `gh pr diff <pr-number> --stat`

Red flags:
- the diff is much larger than the intended follow-up
- GitHub diff endpoints report an oversized PR / too many lines
- `gh pr diff` fails with an oversized diff response such as HTTP 406 `PullRequest.diff too_large`
- the head branch is the same historical feature branch used for the already-merged PR

## Clean replacement recipe

1. Start from the base branch:
   - `git checkout -b <new-followup-branch> origin/main`
2. Cherry-pick only the follow-up commits:
   - `git cherry-pick <commit1> <commit2> ...`
3. Re-run the narrow verification commands that cover the touched files.
4. Re-check scope before opening the replacement PR:
   - `git diff --stat origin/main...HEAD`
   - `git log --oneline origin/main..HEAD`
5. Push the clean branch:
   - `git push -u origin <new-followup-branch>`
6. Open the replacement PR from the clean branch.
7. If a noisy PR was already opened from the historical branch, close it with a short note pointing to the replacement PR.
8. Confirm the replacement PR now points at the clean branch and intended head SHA.

## Why this matters

A branch that was previously used for a merged PR can still be a valid git branch, but a new PR from that branch may include old branch history relative to the base. For follow-up work, a clean branch from the base plus cherry-picked follow-up commits produces a reviewable PR that contains only the intended fixes.
