# Worktree Output Verification

Use this when an Ouroboros Seed run reports success but the target project directory appears unchanged.

## Durable lessons from live verification

1. Seed execution may complete in an isolated Ouroboros worktree rather than mutating the original repo path directly.
2. The worktree path follows this pattern:
   - `~/.ouroboros/worktrees/<repo-name>/orch_<session-or-run-id>/`
3. After `ouroboros_start_execute_seed` or auto-generated execution completes, verify both:
   - the original target repo path
   - the matching worktree path for the session/execution
4. Treat the worktree as the authoritative artifact location when the original repo remains unchanged.
5. When starting execution from a seed path, keep the seed in an allowed location such as:
   - the project directory
   - `~/.ouroboros/seeds/`

## Minimal verification checklist

- Get `job_id`, `session_id`, `execution_id`
- Wait for terminal status with `ouroboros_job_wait`
- Fetch final status with `ouroboros_job_result`
- Inspect the original repo path
- Inspect `~/.ouroboros/worktrees/<repo-name>/orch_*` for the session's artifacts
- Read back exact bytes of created files before claiming success

## Why this matters

Without the worktree check, a successful run can look like a false negative because the original repo path may still contain only the pre-run files.
