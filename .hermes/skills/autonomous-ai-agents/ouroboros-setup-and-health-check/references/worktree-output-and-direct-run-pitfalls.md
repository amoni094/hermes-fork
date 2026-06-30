# Worktree output and direct-run pitfalls

Durable learnings from a live Ouroboros verification pass.

## 1) Completed runs may write into Ouroboros worktrees, not the original repo

Observed successful execution paths:
- `ouroboros auto` generated a Seed and launched a detached execution job.
- standalone `execute_seed` completed successfully.

Verification detail:
- The expected artifact was absent from the original target repo.
- The real artifact existed under:
  - `~/.ouroboros/worktrees/<repo>/orch_*/seed_done.txt`

Implication:
- For setup and smoke-test verification, check both:
  1. recorded job/execution terminal state
  2. actual artifact location on disk
- If the original repo is unchanged, inspect `~/.ouroboros/worktrees/<repo>/` before concluding failure.

## 2) Direct CLI `run --no-orchestrator` can look successful while doing nothing

Observed behavior:
- `ouroboros run workflow <seed> --no-orchestrator ...` exited 0
- `ouroboros run <seed> --no-orchestrator ...` also exited 0
- both only printed:
  - `Would execute workflow from: <seed>`
- no artifact was created in the target repo

Implication:
- Treat that path as preview-like until proven otherwise in the current install.
- Do not accept exit code 0 alone as execution proof.
- Prefer MCP-owned execution paths when you need a real completion proof:
  - `execute_seed`
  - `start_execute_seed`
  - `auto`

## 3) Truthful reporting pattern

For workflow verification, report these separately:
- handoff/seed generation succeeded
- background/detached job reached terminal state
- artifact location verified on disk
- original repo mutated directly vs isolated worktree output

This prevents false negatives (artifact checked only in the source repo) and false positives (preview/no-op CLI returned 0).
