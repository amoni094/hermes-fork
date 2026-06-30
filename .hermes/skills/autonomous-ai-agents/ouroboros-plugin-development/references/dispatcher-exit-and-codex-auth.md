# Dispatcher exit and Codex auth gate

Use this when a local Ouroboros plugin appears to run correctly but `ooo <plugin> ...` still ends with a traceback or when a prepared workflow reaches Codex and every AC fails immediately.

## Dispatcher exit-path pitfall

Symptom:
- Plugin stdout shows a successful prepared result.
- Expected artifacts are written under the caller workspace.
- The top-level `ooo` command still ends with a Typer/Click traceback and non-zero exit.

Observed fix pattern:
- In the fallback plugin dispatcher, raise `typer.Exit(code=...)` rather than `click.exceptions.Exit(code=...)`.
- This preserves the intended shell exit code without dumping a framework traceback after a successful plugin run.

Verification shape:
1. Re-run the same dispatched plugin command in a clean workspace.
2. Confirm exit code is 0 for success cases.
3. Confirm stderr is empty.
4. Confirm plugin artifacts still land in the caller workspace, not the installed plugin tree.

## Codex auth gate before blaming plugin logic

Symptom:
- Prepared seed/handoff validates.
- Ouroboros creates the clean worktree and initializes the Codex runtime.
- Every AC fails almost immediately.

Fast gate:
- Run a minimal Codex smoke test first, e.g. `codex exec 'OK'`.
- If this fails with auth errors such as reused refresh token, expired token, or repeated 401s, treat the workflow failure as an authentication/runtime issue rather than a plugin or seed-contract bug.

Typical evidence shape:
- `refresh_token_reused`
- `token_expired`
- `401 Unauthorized`
- WebSocket or responses endpoint auth failure shortly after session initialization

Interpretation:
- If the smoke test fails, stop short of claiming the plugin or prepared workflow is broken.
- Report that prep/seed/worktree stages succeeded and execution is blocked downstream by Codex auth state.
