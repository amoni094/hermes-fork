---
name: wayland-session-management
description: Broad Wayland desktop session recovery skill covering launch-path tracing, systemd user targets, portal dependencies, and startup-vs-teardown diagnosis.
version: 1.0.0
license: MIT
platforms: [linux]
metadata:
  tags: [wayland, hyprland, gdm, portals, systemd-user, session, troubleshooting]
---

# Wayland Session Management

Use this when a Wayland desktop session starts incompletely, tears down immediately, or loses portal/session functionality. The focus is the real launch path and user-session wiring, not blind config edits.

## Core idea
When a Wayland session misbehaves, first identify:
1. how the session was launched
2. whether the systemd user session came up correctly
3. whether portals failed because the session was inactive
4. whether the desktop actually crashed or was torn down by a later trigger

## When to use
- `graphical-session.target` is inactive or missing.
- `xdg-desktop-portal` fails with dependency errors.
- The compositor starts and then immediately exits or logs out.
- GDM/session-manager selection seems wrong.
- A desktop helper is missing but the session itself is otherwise healthy.

## Workflow

### 1) Establish the launch path
- Check the desktop entry or session launcher in use.
- Read `Exec=` and `TryExec=`.
- Confirm the expected manager binary exists.
- Verify the active session choice is what the user intended.

### 2) Inspect user-session targets
- Read the relevant systemd user units, not just their status.
- Check `graphical-session.target`, portal services, and compositor-specific user targets.
- Watch for `RefuseManualStart=yes` and stop forcing invalid workarounds.

### 3) Reconstruct one failed boot
- Use one boot window and look at the ordering of startup, portal failure, and teardown.
- Distinguish a launch failure from a successful start followed by logout/shutdown.

### 4) Decide the fix path
- If the plain session never becomes healthy, prefer the managed session path when available.
- If the manager binary is missing, verify package availability before changing config.
- If the desktop is healthy but a helper is missing, fix the helper path or script rather than the compositor.
- If the logs show a clean session teardown rather than a compositor crash, audit user-facing exit triggers before changing the compositor itself: keybinds, Waybar modules, power-menu scripts, and UWSM/Hyprland logout wrappers.
- Treat direct `hyprctl dispatch exit` bindings/buttons as high-risk during diagnosis; prefer routing them through an explicit power menu or wrapper so accidental input cannot silently kill the whole session and all user services running inside it.
- When the user migrated from one local agent/app to another, audit residual desktop integration too: `~/.config/autostart/*.desktop`, generated `app-*@autostart.service` units, helper scripts in `~/.local/bin`, and user services whose names still reference the retired app. A stale autostart helper can keep launching the old agent and make the current desktop/session diagnosis misleading.
- If a retired app left behind a useful behavior (for example lid-close locking), remove the branded residue first, then recreate the behavior under a neutral service/script name rather than keeping the old product name in the live session.
- See `references/hyprland-agent-residue-cleanup.md` for the post-migration cleanup pattern.

### 5) Keep temporary debug changes reversible
- If you neutralized logout, reboot, or suspend actions during diagnosis, restore them after the session is healthy.
- Re-validate the compositor config and the live user files after restoration.
- If you replace a direct logout binding with a safer wrapper, verify both the intended UX and the side effect boundary: launching the menu must not trigger `exit.target`, and the explicit logout path must still work when deliberately chosen.

## Practical rules
- Do not try to start invalid session targets from compositor config.
- Do not blame portals before checking the session target state.
- Do not assume a missing helper means the whole desktop is broken.
- Do not keep debugging startup when the logs show the session already reached a healthy state and then got torn down.

## Verification
- Launch path identified.
- User-session units inspected.
- Boot timeline reconstructed.
- Fix path chosen based on real logs.
- Any temporary debug changes were restored and rechecked.

## Notes
More specific workflows that fit under this umbrella include Hyprland/GDM/UWSM session bootstrap, portal dependency recovery, and post-start teardown triage.

Reference:
- `references/hyprland-session-exit-triggers.md` — quick teardown-vs-crash triage plus the safer replacement pattern for direct Hyprland exit bindings/buttons.
