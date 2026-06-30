# Workflow smoke and plugin selection

Use these notes during Ouroboros setup verification when the user wants more than a health check.

## Plugin selection for setup-time verification
- Prefer plugins with a unique namespace or command family to avoid install-time collisions with already-installed plugins.
- Separate three states:
  1. manifest valid
  2. installed + trusted
  3. runtime command exercised successfully
- For runtime verification, prefer either:
  - a static inspection command that completes synchronously, or
  - a plugin backed by tooling already present on the host
- Avoid treating install/trust alone as proof that the plugin is usable.

## Workflow smoke test rules
- `ouroboros auto` expects a git repository. For disposable tests, create a temporary repo first.
- If output says `run_handoff_started`, `execution started`, or prints a job/execution/session ID, treat that as a handoff checkpoint, not completion.
- Wait for the recorded job to reach a terminal state and inspect its result before calling the run successful.
- If the handoff job is interrupted because the owning process exits, report that truthfully and choose a synchronous verification path for the final setup verdict.
