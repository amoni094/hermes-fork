---
name: agent-runtime-stack-debugging
triggers:
  - A plugin prepares artifacts but end-to-end execution still fails
  - A dispatcher reports trust drift, digest mismatch, or 'bytes changed since installation'
  - Debugging the local plugin → dispatcher → workspace → runtime stack by isolating layers
  - Runtime behavior differs from direct plugin execution and root cause is unclear
  - A daemon or background service crashes at startup with an import error or missing-package error
  - hermes doctor says a memory/plugin provider is active but the daemon actually fails to start
description: >
  Use when debugging local plugin → dispatcher → workspace → runtime stacks by isolating layers, proving backend health directly, and preventing mutable install artifacts from contaminating trust or hashing.
related_skills:
  - systematic-debugging
  - hermes-dashboard-troubleshooting
  - autonomous-agent-loop-design
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
- Trusting `hermes doctor` for daemon liveness — it checks plugin install state, not whether the daemon process is actually healthy. A provider can be marked "active" while the daemon is crash-looping. Always probe the daemon port directly (e.g. `curl http://localhost:9177/health` for hindsight).
- Taking an "install X" error message at face value. The package may already be installed but broken due to a transitive dependency version conflict. Always test the import directly in the daemon's venv (`<venv>/bin/python -c "import X"`) and read the full traceback before installing anything.
- **Python version mismatch between daemon venv and system python causes pyc magic errors** — the Hermes daemon venv may run Python 3.11 while the system `python3` is 3.14. Scripts launched by the cron runner that load `.pyc` bytecode compiled for 3.14 will fail with `ImportError: bad magic number`. Confirming mismatch: run `<venv>/bin/python3 --version` and `/usr/bin/python3 --version`; if they differ, check pyc magic with `python3 -c "print(open('<file.pyc>','rb').read(4).hex())"` vs `python3 -c "import importlib.util; print(importlib.util.MAGIC_NUMBER.hex())"`.
- **`spec_from_file_location` returns `None` for non-`.pyc` extensions** — if the backup pyc file has a `.bak` extension, `spec_from_file_location` silently returns `None`, causing `AttributeError: 'NoneType' object has no attribute 'loader'` on the next line. Always use `SourcelessFileLoader` explicitly when loading pyc files with non-standard extensions.
- **`__pycache__/` recompile shadows the real logic file** — when a wrapper script is imported under the wrong Python version, it recompiles a small stub (~4KB) into `__pycache__/` with the wrong magic number, overwriting the slot where the real 35KB logic pyc was. The candidate list in loader scripts must prefer the `.bak` reference copy over `__pycache__/`; check file sizes if suspicious.

## Codex Plugin Runtime Pitfalls (from codex-plugin-runtime-notes.md)

- A plugin can be structurally fixed at the handoff/seed layer while end-to-end runs still fail downstream in the runtime.
- When AC execution fails immediately after runtime startup, inspect structured event logs/DB rows for the **first backend-originated error message** — not just the top-level "Execution failed" summary.
- For Codex CLI specifically, direct smoke tests are decisive: if `codex exec 'OK'` fails with 401/refresh-token errors, treat the orchestrated failure as an **auth-preflight blocker**, not a workflow bug.
- Workspace-local artifact routing is the safer default for installed plugins. Managed output directories avoid mutating the installed plugin tree and reduce trust/digest churn.
- Ignoring Python cache artifacts (`__pycache__/`, `*.pyc`) during install copy is a good defense against trust drift when plugin trees are hashed or re-verified.

## References
- `references/codex-plugin-runtime-notes.md` — concise notes on Codex-backed plugin/orchestrator failure triage, backend-auth smoke tests, and trust-drift mitigation.
- `references/hermes-venv-dependency-drift.md` — exact repair sequence for daemon startup failures caused by transitive Python dependency version conflicts (e.g. hindsight/sentence-transformers/huggingface-hub mismatch). Covers diagnostic triage path and verification steps.
- `references/pyc-interpreter-mismatch.md` — diagnosis and fix pattern for pyc magic number mismatches between Hermes venv (3.11) and system Python (3.14), including SourcelessFileLoader recipe and re-exec guard.

## Verification before claiming success
Do not say the stack is fixed until you have all of:
- a successful prepare/invoke result,
- artifacts written outside the installed plugin tree,
- a passing direct backend smoke test,
- and one successful end-to-end orchestrated run if the user asked for runtime verification.
