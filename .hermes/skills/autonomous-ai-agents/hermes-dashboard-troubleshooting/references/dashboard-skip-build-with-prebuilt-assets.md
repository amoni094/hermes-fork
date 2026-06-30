# Dashboard recovery when startup prints npm-install failure but built assets already exist

Problem class:
- `hermes dashboard` prints `Installing TUI dependencies…` then `npm install failed.`
- user assumes the dashboard did not start
- host may lack native Node build tooling for unrelated workspace dependencies
- however, prebuilt dashboard/TUI assets already exist and are usable

Durable lesson

Treat this as a verification-first recovery case, not an automatic rebuild case.

Checks that matter:
- Is `ui-tui/dist/entry.js` already present?
- Is `hermes_cli/web_dist/index.html` already present?
- Does `http://127.0.0.1:<port>/api/status` respond?
- Does `/chat` render?

Why this happens

Hermes can reach an npm-install path that operates at workspace scope. A root-level install may pull in unrelated native dependencies from other workspaces. Those can fail on lightweight hosts even when the web dashboard and embedded TUI are already built.

Smallest durable recovery path

Use:
- `hermes dashboard --skip-build`

This reuses existing built assets and avoids turning dashboard startup into a full workspace dependency repair task.

What to capture from the session

Capture the pattern, not the host-specific failure details. The durable point is:
- verify real runtime health before assuming npm output equals dashboard outage
- prefer `--skip-build` once known-good assets are present
- only escalate to dependency/toolchain repair if a real rebuild is actually needed
