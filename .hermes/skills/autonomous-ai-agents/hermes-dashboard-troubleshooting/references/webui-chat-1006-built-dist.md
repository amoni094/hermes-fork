# WebUI `/chat` code 1006 with an existing built TUI

Problem class:
- Hermes dashboard loads
- `/chat` opens
- browser reports `session ended (code 1006)`
- dashboard log shows `npm install failed.` during `/api/pty` startup

Durable diagnosis

The PTY websocket path can fail even when the dashboard frontend is healthy.

Typical chain:
1. Browser connects to `/api/pty`.
2. `hermes_cli.web_server._resolve_chat_argv()` asks `hermes_cli.main._make_tui_argv()` how to launch the TUI.
3. `_make_tui_argv()` decides dependencies need reinstall/build.
4. On a lightweight host, npm hits an optional native rebuild path (for example `node-pty`) and fails because build tooling is missing.
5. `/api/pty` cannot start the PTY child, and the browser collapses that into websocket close code `1006`.

What made this class of issue tricky

A built TUI bundle may already exist and be perfectly usable:
- `ui-tui/dist/entry.js`

So the failure is not "chat cannot run".
It is "chat is trying to rebuild when it should have reused the built bundle".

Fix pattern

Patch `hermes_cli/web_server.py::_resolve_chat_argv()` so it:
- checks for `PROJECT_ROOT / "ui-tui" / "dist" / "entry.js"`
- resolves `node`
- prefers `node --expose-gc <dist/entry.js>` when that built bundle exists
- falls back to `_make_tui_argv()` only when no usable built bundle exists

Why this is durable

This avoids making dashboard chat depend on workspace-root npm health during each websocket startup. That is a class-level reliability improvement for Hermes dashboard deployments where the built TUI artifact exists but native Node build prerequisites may not.

Verification recipe

1. Restart the dashboard.
2. Confirm it is listening.
3. Open a websocket directly to `/api/pty` with a valid token/ticket.
4. Send an initial resize escape.
5. Successful fix = PTY bytes arrive on connect instead of an immediate close.
6. Then verify `/chat` in the browser shows a live model/status instead of `code 1006`.

Non-durable details intentionally excluded

Do not encode a permanent claim that npm, node-pty, or build tooling is broken. The durable lesson is the startup preference order: reuse the existing built TUI bundle before attempting reinstall/rebuild during dashboard chat startup.
