---
name: hermes-dashboard-troubleshooting
triggers:
  - Hermes dashboard or WebUI fails to start or shows a blank page
  - Chat sidebar is missing, broken, or not showing conversations
  - Event feed websocket errors appearing in the dashboard
  - Troubleshooting the Hermes web UI after a config change or update
  - DeletedWalGenerationError or session_search WAL conflict after gateway restart
  - Dashboard not starting after gateway restart
  - lsof shows stale state.db-wal holders after gateway stop
description: >
  Use when troubleshooting Hermes dashboard/WebUI startup, chat sidebar, and event-feed issues with build-first and websocket verification steps.
version: 1.0.0
author: Hermes Agent
license: CC0-1.0
created_by: agent
related_skills:
  - hermes-agent
  - hermes-session-hygiene
  - wayland-session-management
---

# Hermes Dashboard Troubleshooting

Use when the Hermes dashboard/WebUI is up but partially broken, fails to start cleanly, or the embedded chat/sidebar says the event feed is disconnected and tool calls are missing.

## Durable pitfall: `/chat` 1006 with an existing built TUI

If dashboard `/chat` dies with websocket code `1006` and the dashboard logs show `npm install failed.` during PTY startup, check whether `ui-tui/dist/entry.js` already exists.

Why this happens:
- `/api/pty` reaches `_resolve_chat_argv()`
- `_resolve_chat_argv()` calls `_make_tui_argv()`
- `_make_tui_argv()` may decide it needs an npm install/build at connect time
- on lightweight hosts, that path can fail because native build tooling for optional Node dependencies is missing
- the browser then surfaces the PTY startup failure as `session ended (code 1006)`

Durable fix pattern:
1. In `hermes_cli/web_server.py::_resolve_chat_argv()`, prefer an already-built `ui-tui/dist/entry.js` bundle when it exists.
2. Launch it directly with `node --expose-gc <dist/entry.js>`.
3. Fall back to `_make_tui_argv()` only when no usable dist bundle exists.
4. Restart the dashboard.
5. Verify `/api/pty` directly; successful verification is receiving PTY bytes on connect instead of an immediate close.

This is the durable lesson: dashboard chat should prefer a known-good built TUI bundle over an unnecessary reinstall/rebuild path during websocket startup.

## Triggers

- `hermes dashboard` fails during startup or exits before binding.
- The dashboard loads but the chat sidebar says `events feed disconnected — tool calls may not appear`.
- Embedded chat works only partially: terminal pane renders, but tool-call events do not show in the sidebar.
- You need to verify whether `/api/pub` → `/api/events` rebroadcasting is healthy.

## Core rule

Do not stop after reading code or logs. Restore a working dashboard and verify the event path with a real round-trip.

## Workflow

1. Confirm the dashboard state.
   - Check whether a dashboard process is already running.
   - Check whether the default port (`127.0.0.1:9119`) is listening.
   - If startup recently failed, inspect the dashboard process output first.

2. Treat build/runtime separately.
   - If `hermes dashboard` reports Web UI build or npm-install failures, fix the frontend assets first.
   - From the repo root's `web/` directory:
     - `npm install`
     - `npm run build`
   - Hermes writes the built bundle into `hermes_cli/web_dist/`.

3. Relaunch without rebuilding when the assets are already known-good.
   - Start with:
     - `hermes dashboard --no-open --skip-build`
   - Use `--skip-build` after a successful manual build to avoid repeating build-time failures during service recovery.

4. Verify the browser-facing dashboard.
   - Confirm the page loads at `http://127.0.0.1:9119`.
   - Confirm the Chat page renders and the sidebar reaches `live` state.

5. Verify the event-feed path directly.
   - The structured tool-call sidebar depends on a websocket rebroadcast chain:
     - PTY child publishes to `/api/pub?channel=...`
     - browser sidebar subscribes to `/api/events?channel=...`
   - If the UI still looks suspicious, perform a direct websocket round-trip:
     - connect a subscriber to `/api/events`
     - connect a publisher to `/api/pub`
     - send a JSON frame like `{"method":"event","params":{"type":"tool.start",...}}`
     - confirm the subscriber receives the same frame
   - This proves the sidebar transport is healthy even if the visual UI is lagging or the session is idle.

## WAL conflict: dashboard surviving gateway restart

Symptom: `session_search` (and any DB consumer) throws `DeletedWalGenerationError` after a gateway restart. `lsof ~/.hermes/state.db-wal` shows a surviving process — usually the dashboard.

Root cause: `hermes-dashboard.service` runs in its own cgroup. `KillMode=control-group` on the gateway only kills the gateway cgroup; the dashboard survives, keeping its old-generation WAL/SHM file handles open. The new gateway opens a fresh WAL generation and detects the inode mismatch.

There are two classes of stale holder:
1. Process holds a `(deleted)` WAL inode — WAL was unlinked while the process had it open.
2. Process holds a WAL inode whose number doesn't match the current on-disk WAL — old-generation WAL open after a rotation (common when dashboard survives a gateway restart).

Emergency recovery:
```
kill -9 <dashboard-pid> <gateway-pid>
# Wait: lsof ~/.hermes/state.db-wal  (should return empty)
hermes gateway restart
# Dashboard auto-starts via gateway Wants= (see Durable fix below)
```

Durable fix — three components working together:
1. `hermes-dashboard.service`: add `BindsTo=hermes-gateway.service` and `After=hermes-gateway.service`. Dashboard stops when gateway stops (BindsTo), releases WAL FDs before new gateway opens DB.
2. Gateway drop-in `~/.config/systemd/user/hermes-gateway.service.d/dashboard-wants.conf`: add `Wants=hermes-dashboard.service`. Dashboard auto-starts when gateway starts. (Required because BindsTo propagates stop but suppresses `Restart=` — dashboard stays dead after gateway restart without this.)
3. `wal-guard.sh` (ExecStartPre on gateway): run two lsof passes before each gateway start — Pass 1 kills `(deleted)` holders, Pass 2 kills wrong-generation (inode-mismatch) holders. See `references/wal-guard-design.md` for full implementation details.

Pitfalls:
- `BindsTo=` + `Restart=always` on the dashboard does NOT cause a restart loop — systemd suppresses `Restart=` when a unit is stopped by dependency propagation (BindsTo stop path). Empirically confirmed: NRestarts stays 0 after gateway stop.
- The gateway `Wants=` drop-in is required; without it the dashboard stays inactive after gateway restart, silently.
- `systemd-analyze verify --user` must pass cleanly after any unit file change.

## Pitfalls

- A user systemd autostart unit can keep re-triggering the same unnecessary npm-install path at every boot. When built dashboard/TUI assets already exist, patch the unit's `ExecStart=` to add `--skip-build`, then `systemctl --user daemon-reload && systemctl --user restart hermes-dashboard.service`.

- `hermes dashboard` can fail only because the frontend dependencies/assets are missing or stale. In that case the backend/websocket code may be fine; rebuild first instead of patching server code immediately.
- A startup-side `Installing TUI dependencies…` → `npm install failed.` message does not, by itself, prove the dashboard failed to come up. If prebuilt assets already exist (`ui-tui/dist/entry.js`, `hermes_cli/web_dist/index.html`), verify the live HTTP listener and `/chat` before treating it as a real outage.
- A working dashboard page does not prove the tool-call sidebar transport is working. Verify `/api/pub` and `/api/events`, not just `/`.
- Important auth pitfall during event-feed verification: direct websocket probes to `/api/pub` or `/api/events` will 403 unless they include the same auth shape the SPA uses (`?token=` in loopback mode, or a minted ws ticket in gated mode). A bare `ws://.../api/events?channel=...` failure is not proof the transport is broken.
- Practical verification pattern: when checking the sidebar transport from a live page, read `window.__HERMES_SESSION_TOKEN__` / `window.__HERMES_AUTH_REQUIRED__`, open authenticated `/api/pub` + `/api/events` sockets with the page's auth mode, send a small JSON event frame, and confirm the subscriber receives it.
- After confirming built assets exist, prefer `hermes dashboard --skip-build` as the smallest recovery path. This avoids unnecessary workspace-root npm installs that can drag in unrelated native dependencies.
- If manual npm reproduction is needed, distinguish workspace scopes: root-level installs can fail on optional/native deps from unrelated workspaces (for example `node-pty`) even when the dashboard/web assets are already good enough to run.
- After a manual successful build, prefer `--skip-build` for recovery and verification runs. It reduces moving parts.
- If you intentionally kill a broken dashboard and restart it, Hermes may later surface an `[IMPORTANT: Background process ... completed]` notice for the old tracked launcher. Do not treat that notice as proof the current dashboard died. Verify the live listener and current PID with `ss` + `ps`, then check `/chat` again.
- Port-history pitfall: a user may remember an older local web app port and assume Hermes moved or broke. Before changing the Hermes dashboard port, inspect the user systemd unit's `ExecStart=` and compare it with the active listeners. If the remembered port is free and not referenced by a unit, it may belong to a different standalone app rather than Hermes itself.
- Coexistence pitfall: Hermes can be healthy on its pinned port while a sidecar local app on another port has simply stopped because it was launched ad hoc (for example `python3 app.py`) instead of via a user service. If the user wants both, keep Hermes on its configured port, start the sidecar app separately, and verify both with `ss` plus a real HTTP 200 check.
- When diagnosing the sidebar banner, distinguish these layers:
  - page load / static assets
  - PTY websocket (`/api/pty`)
  - sidecar gateway websocket (`/api/ws`)
  - event rebroadcast websocket (`/api/pub` + `/api/events`)

## References

- `references/event-feed-recovery.md` — websocket rebroadcast recovery recipe for missing tool-call events.
- `references/webui-chat-1006-built-dist.md` — durable fix for `/chat` code 1006 when PTY startup tries to rebuild instead of reusing an existing built TUI.
- `references/dashboard-restart-process-noise.md` — how to tell a stale process-completion notice from the current live dashboard state.
- `references/systemd-autostart-skip-build.md` — user-systemd recovery pattern for dashboard autostart when prebuilt assets exist and rebuilds are unnecessary.
- `references/dashboard-skip-build-with-prebuilt-assets.md` — recovery pattern when startup prints npm-install failure even though existing dashboard/TUI assets are usable.
- `references/port-separation-hermes-vs-sidecar-apps.md` — how to distinguish the Hermes dashboard port from a separate local sidecar app and keep both available.
- `references/wal-guard-design.md` — wal-guard.sh two-pass structure, column layout assumptions, empty-inode race fix, lsof -n -P flags, and systemd coupling pattern.

## Verification checklist

- Dashboard is listening on the expected host/port.
- The main page loads.
- Chat page renders.
- Sidebar no longer shows the disconnected banner.
- A direct `/api/pub` → `/api/events` websocket test succeeds.

## Reference

- `references/event-feed-recovery.md` — concise recovery and websocket verification recipe for the disconnected event-feed symptom.
