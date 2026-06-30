# Systemd autostart for dashboard when startup-time npm install is unnecessary

Problem class:
- `hermes dashboard` works when launched manually with `--skip-build`
- a user systemd service starts the dashboard without `--skip-build`
- startup logs show `Installing TUI dependencies…` followed by `npm install failed.`
- prebuilt assets already exist, so the service is failing or starting noisily for the wrong reason

Durable diagnosis

When `ui-tui/dist/entry.js` and `hermes_cli/web_dist/index.html` already exist, the smallest reliable autostart path is to reuse those built assets. A user service that launches plain `hermes dashboard` may re-enter the workspace npm-install path on every boot, which is unnecessary and can trip optional native rebuilds.

Fix pattern

1. Inspect the user unit, typically `~/.config/systemd/user/hermes-dashboard.service`.
2. Change `ExecStart=` to include `--skip-build`, for example:
   `ExecStart=/path/to/hermes dashboard --no-open --skip-build --host 127.0.0.1 --port 9119`
3. Reload the user manager:
   `systemctl --user daemon-reload`
4. Enable/restart the service:
   `systemctl --user enable hermes-dashboard.service`
   `systemctl --user restart hermes-dashboard.service`
5. Verify both service state and HTTP health:
   - `systemctl --user status hermes-dashboard.service`
   - `curl http://127.0.0.1:9119/api/status`
   - load `/chat` and confirm the terminal input renders

Persistence option

If the user wants the dashboard to survive logout, enable linger for that user:
- `loginctl enable-linger <user>`
- verify with `loginctl show-user <user> -p Linger`

What to capture as the lesson

Do not encode the transient package failure itself as the rule. The durable lesson is: when the dashboard already has known-good built assets, systemd autostart should use `--skip-build` so startup does not depend on workspace npm health.