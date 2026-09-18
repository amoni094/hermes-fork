When a repo-level AGENTS.md adds mandatory repo-specific verification beyond generic tests, treat those checks as part of the scoped fix loop before commit/push.

Patterns reinforced by this session:
- After implementing a focused UI change, run the smallest relevant proof set first (targeted unit/integration tests), then run repo-mandated preflight gates before commit/push.
- If the repo requires code-intelligence review steps (for example GitNexus impact/detect-changes), attempt them explicitly and report the result.
- If a required verification tool crashes or its index is stale/corrupt, do not silently skip it and do not claim it passed. Retry once with the documented recovery step if available, then finish the rest of verification and call out the blocker clearly in the final report.
- Good final report shape for scoped fixes in dirty repos: files changed, tests run, repo preflight result, commit SHA/message, push result, and any mandatory verification step that remained blocked.

Concrete example from this session:
- UI change: add a first-class Dashboard Maker entry on the Dashboards page while preserving the existing workflow-builder entrypoint.
- Shared follow-up refactor: extract shared dashboard-maker URL/popup logic into a helper so the dashboards page and workflow builder use the same builder-mode URL and popup-safety behavior.
- Verification set that paid off: targeted Vitest for the changed surfaces, TypeScript noEmit, repo git-preflight wrapper, then commit/push.
- Important reporting behavior: GitNexus impact/detect-changes crashed in native code; that blocker should be surfaced explicitly instead of being omitted or treated as passed.