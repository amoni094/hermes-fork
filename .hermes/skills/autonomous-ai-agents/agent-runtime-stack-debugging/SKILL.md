---
name: agent-runtime-stack-debugging
description: Debug local plugin → dispatcher → workspace → runtime stacks by isolating layers, proving backend health directly, and preventing mutable install artifacts from contaminating trust or hashing.
---

# Agent Runtime Stack Debugging

Use when a local agent workflow crosses several layers — plugin code, dispatcher/install logic, workspace setup, and a backend runtime such as Codex CLI — and failures could be misattributed to the wrong layer.

## When to use
- A plugin prepares artifacts but end-to-end execution still fails.
- A dispatcher reports trust drift, digest mismatch, or "bytes changed since installation".
- A runtime-backed orchestrator fails after startup and it is unclear whether the problem is the workflow or the backend.
- Clean repos behave differently from lived-in workspaces.

## Core rule: debug one layer at a time
1. Verify artifact generation first.
   - Confirm the plugin emits the expected handoff / seed files.
   - Read the generated seed and verify the recommended follow-on command matches the actual artifact type.
2. Verify dispatcher/install behavior separately.
   - Check whether invocation writes into the installed plugin tree. It should not.
   - Prefer a workspace-local managed output directory passed by the dispatcher/runtime.
3. Verify workspace setup separately.
   - Reproduce in a clean repo to separate dirty-checkout and worktree problems from plugin logic.
4. Verify backend runtime directly.
   - Run the backend CLI outside the orchestrator with a minimal smoke test before blaming orchestration.
   - Example: `codex exec 'OK'` or equivalent single-prompt native call.
5. Only after those pass should you debug orchestrator decomposition / AC execution.

## High-value checks
- Compare the failing workspace with a clean repo run.
- Capture stdout/stderr for both plugin dispatch and direct runtime execution.
- If the orchestrator stores events in SQLite or structured logs, inspect those records for the first concrete backend error instead of stopping at the top-level "Execution failed" summary.
- Treat auth failures, expired tokens, and reused refresh tokens as backend-preflight blockers, not workflow logic bugs.

## Prevent trust/hash drift in installed plugins
When a plugin is installed into a managed plugin directory:
- Do not write runtime artifacts into the installed plugin tree.
- Route artifacts to a workspace-local output directory via dispatcher-provided env vars.
- Exclude volatile files from install copies / digest subjects when possible:
  - `__pycache__/`
  - `*.pyc`
  - similar generated cache artifacts
- Clean caches before reinstalling if trust drift is already present.

## Practical workflow
1. Prepare or invoke the plugin in a clean workspace.
2. Confirm artifacts land under a workspace-local managed directory, not under the installed plugin home.
3. Reinstall/retrust only after cleaning volatile cache files if the trust subject may have changed.
4. Run a direct backend smoke test.
5. If the smoke test fails, stop blaming orchestration and fix backend auth/config first.
6. If the smoke test passes, inspect orchestrator logs/events to find the first failing AC/session.

## Pitfalls
- Mistaking a successful preparation step for a successful end-to-end runtime.
- Chasing plugin code when the real blocker is backend authentication.
- Allowing installed plugin directories to accumulate runtime output or Python cache files, then trusting those mutable bytes.
- Debugging only in a dirty workspace and missing that the failure is checkout-state dependent.

## References
- `references/codex-plugin-runtime-notes.md` — concise notes on Codex-backed plugin/orchestrator failure triage, backend-auth smoke tests, and trust-drift mitigation.

## Verification before claiming success
Do not say the stack is fixed until you have all of:
- a successful prepare/invoke result,
- artifacts written outside the installed plugin tree,
- a passing direct backend smoke test,
- and one successful end-to-end orchestrated run if the user asked for runtime verification.
