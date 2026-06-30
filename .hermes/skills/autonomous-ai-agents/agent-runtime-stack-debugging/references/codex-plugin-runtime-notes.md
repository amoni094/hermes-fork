# Codex-backed plugin/runtime debugging notes

Session-derived durable pattern:

- A plugin can be structurally fixed at the handoff/seed layer while end-to-end runs still fail downstream in the runtime.
- When AC execution fails immediately after runtime startup, inspect structured event logs/DB rows for the first backend-originated error message.
- For Codex CLI specifically, direct smoke tests are decisive: if `codex exec 'OK'` fails with 401 / refresh-token errors, treat the orchestrated failure as an auth-preflight blocker, not a workflow bug.
- Workspace-local artifact routing is the safer default for installed plugins. Managed output directories avoid mutating the installed plugin tree and reduce trust/digest churn.
- Ignoring Python cache artifacts during install copy is a good defense against trust drift when plugin trees are hashed or re-verified.
