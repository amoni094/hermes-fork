---
name: silverblue-system-update-trigger
description: Use when the user asks for a system update, or similar phrasing like update the system or check for updates, in chat on this Fedora Silverblue host. Routes the request to the existing deterministic update script instead of improvising rpm-ostree, flatpak, or dnf commands.
triggers:
  - user asks to update the system, run updates, or check for OS updates on Fedora Silverblue
  - system update phrase — routes to deterministic rpm-ostree/flatpak update script
  - user asks what packages are installed or if the system is current
  - NOT for Hermes-only update — use hermes-agent-independent-update-protocol for that
related_skills:
  - hermes-agent-independent-update-protocol
---

# Silverblue System Update Trigger

## Why this exists
On 2026-07-04 a chat request for "system update" was handled by improvising
`rpm-ostree upgrade --check` directly. That flag is known-flaky (false
positives on pending package counts), which triggered an unnecessary
investigation. The fix already existed: a deterministic script that compares
rpm-ostree deployment checksums before/after instead of trusting `--check`,
and also runs flatpak, toolbox dnf, Hermes self-update, driver/firmware
checks, and managed git repo fast-forwards.

That script is *also* already scheduled to run automatically once per day at
first login via a systemd user unit (`daily-silverblue-update.service`,
triggered by `daily-silverblue-update-login-trigger.sh`) — zero LLM tokens,
zero chat involvement. This skill only covers the ad hoc chat-triggered case.

## Rule
When the user asks for a system update in chat:

1. Do NOT construct rpm-ostree / flatpak / dnf commands by hand.
2. Run the existing script directly, but disable its built-in Hermes
   self-update step so it doesn't race the more thorough agent-driven
   Hermes protocol (see below):
   ```
   terminal(command="HERMES_BIN=/nonexistent ~/.hermes/scripts/daily-silverblue-update.sh", timeout=600)
   ```
   (or the thin wrapper `~/silverblue-update-all.sh`, which just execs the
   same script — either is fine, they're equivalent; apply the same
   `HERMES_BIN=/nonexistent` override).
   Use timeout=600 — Flatpak updates (e.g. Chromium ~164 MB) can take 3-4
   minutes alone, and 300s is not enough.
3. Separately, run the Hermes-agent self-update using the
   `hermes-agent-independent-update-protocol` skill — dirty-check, stash if
   needed, forced backup, foreground update run (timeout=600), verification,
   and automatic rollback on failure. This replaces relying on the script's
   own skip-on-dirty/no-verify Hermes step for the chat-triggered case; that
   step remains unmodified for the unattended daily systemd timer.
4. Summarize the script's log output and exit code in plain language:
   - What was updated (rpm-ostree, flatpak user/system, toolbox dnf, Hermes,
     managed repos).
   - Whether a reboot is required (script logs this explicitly and fires a
     desktop notification if so — no need to duplicate that check).
   - Any step that failed, using the script's own failure classification
     (sudo/network/other) rather than re-diagnosing from scratch.
   - If the script exits non-zero but some steps completed, report partial
     success clearly: state which steps succeeded and which failed, rather
     than treating the whole run as broken.
5. Only fall back to manual commands / investigation if the script itself
   exits with an "other" (unclassified) failure that isn't self-explanatory
   from its log line.

## Partial failure interpretation
The script exits 1 if any step fails, but downstream steps still run. A
non-zero exit code does not mean nothing was updated. Always read the per-step
log lines to determine actual outcome:
- rpm-ostree dep conflict: OS not updated, reboot not needed. Other steps
  (flatpak, toolbox, firmware) continue and may succeed independently.
- Managed repo dirty: expected on active dev repos — not a failure, just skipped.
- Flatpak updates with rpm-ostree failure: valid partial outcome, report both.
- Reboot notification service already loaded: `Failed to start transient service
  unit: Unit reboot-required-notify.service was already loaded or has a fragment
  file.` — benign, means a prior run already queued the notification. The reboot
  IS required; the desktop notification was simply already sent. Do not treat
  this as a reboot-step failure — report the reboot requirement normally.

See `references/rpm-ostree-layered-package-conflicts.md` for the known
Hyprland/wayland conflict pattern, remediation options, and the LocalPackage
restore procedure (including the GNOME Software transaction-cancel pitfall)
for after the OS update completes.

## rpm-ostree layered package conflicts (Hyprland/libwayland pattern)

**Symptom**: `rpm-ostree upgrade` fails with depsolve error — COPR package built against wayland 1.24.x, base image updated to 1.25.x.
Pattern: `cannot install both libwayland-client-1.24.0 from fedora and libwayland-client-1.25.0 from @System`

**Remediation options**:
- A) Wait for COPR rebuild (recommended if Hyprland is primary session)
- B) `rpm-ostree uninstall hyprland hypridle hyprlock xdg-desktop-portal-hyprland` → reboot → reinstall (only viable with parallel GNOME session)
- C) Pin and wait — Flatpak, toolbox DNF, firmware updates still run; rpm-ostree won't update until conflict resolves

**LocalPackages vs LayeredPackages** (critical distinction):
- LocalPackages = installed from `.rpm` files — `rpm-ostree install <name>` fails with "Packages not found"
- Must reinstall from original `.rpm` files: check `~/ricing-rpms/recover-*/`, `~/Downloads/`, then dnf caches
- Stash: `~/ricing-rpms/recover-20260629/` contained the Hyprland RPMs

**GNOME Software transaction conflict**: If the script fails with `Transaction in progress: upgrade (check only)` (initiator is usually `gnome-software.service`, especially when `AutomaticUpdates: stage` is on), do **not** assume cancel+retry is enough. Canceling often just lets GNOME Software grab another check-only transaction within 1s (observed 2026-08-29: `rpm-ostree cancel && sleep 2` still lost the race). Poll `rpm-ostree status` until `State:` is not `busy`, then immediately re-run the daily script. A prior `AvailableUpdate: Diff: N upgraded` from the check-only tx can be a false lead — trust the script's later `No upgrade available.` / checksum comparison.

See `references/rpm-ostree-layered-package-conflicts.md` for the full wayland conflict pattern and LocalPackage restore procedure.

## Token efficiency rationale
The chat-triggered path should cost one tool call (script exec) + one short
summary. All upgrade logic, retry/network-wait handling, and failure
classification already live in the script — re-deriving any of that in
context burns tokens and risks reintroducing bugs (like the `--check`
false-positive) that the script already fixed.

## Related
- Recurring/automatic case is already covered by the systemd unit, not by
  Hermes cron — do not add a duplicate Hermes cron job for daily updates.
- If the systemd unit itself needs debugging (e.g. it failed at the Hermes
  self-update step because the update-check output format changed), that's
  a separate script-maintenance task, not a chat-improvisation one.
