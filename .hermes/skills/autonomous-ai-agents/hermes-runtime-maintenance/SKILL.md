---
name: hermes-runtime-maintenance
description: Manage live Hermes processes and user services safely, then perform runtime updates and verify the real post-update state on local Linux hosts.
version: 1.0.0
author: Hermes Agent
license: CC0-1.0
created_by: agent
---

# Hermes Runtime Maintenance

Use when the user wants live Hermes runtime cleanup or maintenance on the current machine, especially:
- kill other Hermes sessions but keep the current one alive
- stop or restart dashboard/gateway services
- update Hermes itself
- run broad local update passes on Fedora Atomic / Silverblue-style hosts

## Goals
1. Preserve the current Hermes session while operating on sibling Hermes processes.
2. Stop service-managed Hermes components by service name, not just by PID.
3. Distinguish the current session from its helper children before killing anything.
4. Verify updates with the real post-update state, not with preview output alone.

## Core rules
1. Identify the current Hermes parent process first and protect it.
2. Treat helper children as part of the current session unless proven otherwise:
   - MCP sidecars
   - stealth-browser-mcp
   - qmd / FlowState helpers
   - hindsight-api
3. If dashboard or gateway were launched as user systemd services, stop them with `systemctl --user stop ...` instead of killing their PIDs directly.
4. After stopping services, verify both process state and service state.
5. On Fedora Atomic / Silverblue, use `rpm-ostree` for host updates and `flatpak update` for Flatpaks.
6. Treat `rpm-ostree --check` / preview output as advisory only; trust the result of the actual `rpm-ostree upgrade` run plus `rpm-ostree status`.

## Workflow: kill all Hermes sessions except this one
1. Print the current shell PID, PPID, and session ID.
2. Enumerate Hermes-related processes with PID, PPID, SID, elapsed time, and command.
3. Identify the current Hermes process and preserve:
   - the current Hermes parent PID
   - its helper children
4. Separate other Hermes activity into:
   - plain sibling Hermes sessions
   - user services such as `hermes-dashboard.service` and `hermes-gateway.service`
5. Stop service-managed components through systemd first.
6. Kill any remaining non-service sibling Hermes processes.
7. Re-check `ps` and `systemctl --user` to confirm only the current session and its helpers remain.

## Durable pitfall: manual PID kills are not enough for service-managed Hermes
If `hermes dashboard` or the gateway is running as a user systemd service, killing the visible process tree may not achieve the user's intent:
- systemd may respawn it
- or the service may remain in a failed state that still matters operationally

Durable fix pattern:
1. Inspect `systemctl --user --type=service --all | grep -i hermes`.
2. Stop `hermes-dashboard.service` and/or `hermes-gateway.service` explicitly when they are the unwanted sessions.
3. Re-check the service states after the stop.
4. Report if a service is now `inactive/dead` versus `failed` so the next action is obvious.

## Workflow: update Hermes and local package surfaces
1. Record current state first:
   - `hermes --version`
   - OS / kernel
   - `rpm-ostree --version`
   - `flatpak --version`
2. Run `hermes update`.
3. Verify with `hermes --version` after the update, not just the updater's success banner.
4. On Fedora Atomic / Silverblue:
   - run `rpm-ostree upgrade`
   - run `flatpak update -y`
   - run `fwupdmgr get-updates` when the user asked for a broad system update rather than Hermes-only maintenance
5. Verify final state with:
   - `hermes --version`
   - `rpm-ostree status`
   - a note about whether Flatpak had anything to do
   - a note about firmware update state when `fwupdmgr` was checked

## Durable pitfall: `fwupdmgr get-updates` may return exit code 2 for "no updates available"
Do not treat a non-zero exit from `fwupdmgr get-updates` as an automatic failure.

Interpretation rule:
- if the output ends with `No updates available`, treat that as a successful negative check even when the exit code is 2
- reserve failure reporting for transport/runtime errors or output that does not clearly indicate the no-updates state

Operational guidance:
1. Read the human output, not just the exit code.
2. Report "no firmware updates available" when the command explicitly says so.
3. Only escalate when `fwupdmgr` errors without a clear no-updates message.

## Durable pitfall: rpm-ostree preview output can disagree with the real upgrade result
A common confusing state is:
- `rpm-ostree upgrade --check` or `rpm-ostree status` shows `AvailableUpdate`
- but the actual `rpm-ostree upgrade` run returns `No upgrade available.`

Treat this as a verification-order issue, not proof that the update failed.

Durable rule:
- use preview/check output only for discovery
- use the actual `rpm-ostree upgrade` result plus the final `rpm-ostree status` readback as the source of truth
- if they disagree, report the mismatch explicitly instead of claiming an update was applied

## Durable pitfall: `AvailableUpdate` can be a stale cached-update record
A stronger diagnostic than the human-readable status output is `rpm-ostree status --json`.

When `rpm-ostree status` still shows `AvailableUpdate` after a real `rpm-ostree upgrade` returned `No upgrade available.`, inspect:
- `cached-update.update-sha256`
- the booted deployment `checksum`
- `cached-update.ref-has-new-commit`
- `cached-update.rpm-diff`

Interpretation rule:
- if `cached-update.update-sha256` matches the booted deployment checksum, and `ref-has-new-commit` is `false`, there is no real newer deployment
- in that case the visible `AvailableUpdate` banner is stale cached metadata, not an unapplied host update

Operational guidance:
1. Confirm the mismatch with `rpm-ostree status --json` before claiming anything is pending.
2. You may try `rpm-ostree cleanup -m`, `rpm-ostree cleanup -p`, and `rpm-ostree cleanup -b`, but they may not clear the stale banner.
3. If the real upgrade path says no update is available and the JSON fields above confirm no new commit, report the system as up to date and describe the banner as harmless stale cache state.
4. Recommend a reboot as the likely cleanup step, then re-check `rpm-ostree status` afterward.

## Durable pitfall: gateway can restart "healthy" but with all messaging platforms disabled
After `hermes update` or a manual gateway restart, `hermes-gateway.service` may come back as `active (running)` while the runtime logs say `No messaging platforms enabled.` This can happen when valid platform credentials still exist in `~/.hermes/.env` but the persisted config has an explicit disable such as `platforms.telegram.enabled: false`.

Interpretation rule:
- treat `systemctl --user status hermes-gateway` as only a process-health check
- also verify platform-connectivity health in `hermes gateway status` or `~/.hermes/logs/gateway.log`
- if env credentials exist but the platform remains disabled, inspect `config.yaml` for `platforms.<name>.enabled: false`

Operational guidance:
1. After gateway restarts, verify both service state and adapter state.
2. If logs show `No messaging platforms enabled.` but `.env` still contains the expected token(s), inspect `platforms:` in `~/.hermes/config.yaml`.
3. Re-enable the intended platform explicitly, e.g. `hermes config set platforms.telegram.enabled true`.
4. Restart the gateway and confirm a real adapter connection line such as `Connected to Telegram` / `✓ telegram connected`, not just `active (running)`.

## Verification checklist
## Durable pitfall: a healthy gateway service can still be functionally disconnected after an update
After `hermes update`, the gateway service may restart cleanly but come back with zero active messaging adapters if config now explicitly disables a platform that still has valid credentials in `.env`.

Typical symptom:
- `systemctl --user status hermes-gateway` looks healthy
- but `hermes gateway status` / `gateway.log` says `No messaging platforms enabled.`
- meanwhile the environment still contains valid platform credentials (for example Telegram tokens)

Durable fix pattern:
1. After any gateway-affecting update or restart, verify functional connectivity, not just service liveness.
2. Check both:
   - `hermes gateway status`
   - recent `~/.hermes/logs/gateway.log` for real adapter connect lines such as `Connected to Telegram` / `✓ telegram connected`
3. If the service is up but no platforms are enabled, inspect config for explicit platform disables (for example `platforms.telegram.enabled: false`).
4. Re-enable the intended platform in config, then restart the gateway and verify the actual adapter reconnect in logs.
5. Report the distinction clearly: `service active` is not the same as `platform connected`.

## Verification checklist
- Current Hermes session is still alive.
- Unwanted sibling Hermes sessions are gone.
- Dashboard/gateway service state matches the intended stop/start result.
- If you intentionally restarted dashboard or gateway, verify the live replacement process by PID/port/listener instead of assuming the process you launched remained authoritative.
- If repo-side Python/config changes were made during the maintenance pass, explicitly note whether the current live CLI/chat process is still an older in-memory session that needs its own manual restart.
- Hermes update was verified with a fresh version check.
- If the gateway was restarted, functional platform connectivity was verified in `hermes gateway status` and/or gateway logs — not just systemd `active` state.
- `rpm-ostree upgrade` was actually run.
- Flatpak update was actually run.
- Final report distinguishes:
  - updated successfully
  - already up to date
  - preview/status mismatch

## References
- `references/runtime-maintenance-command-patterns.md` — compact command patterns for preserving the current Hermes session, stopping service-managed siblings, and verifying Atomic-host updates.
- `references/rpm-ostree-stale-cached-update-diagnosis.md` — JSON-first diagnosis for stale `AvailableUpdate` banners where no real new deployment exists.

## Overlap note
This overlaps with `hermes-dashboard-troubleshooting` for dashboard-specific service recovery and with `hermes-agent` for general Hermes CLI usage. Keep this skill focused on live process/service maintenance and update verification rather than feature configuration or web UI debugging.
