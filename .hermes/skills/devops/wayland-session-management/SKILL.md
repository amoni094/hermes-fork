---
name: wayland-session-management
triggers:
  - graphical-session.target is inactive or missing on a Wayland desktop
  - xdg-desktop-portal fails with dependency errors or portal services are not starting
  - Broad Wayland desktop session recovery needed (launch-path tracing, systemd user targets, portal dependencies)
  - A Wayland compositor or session manager is failing to start or crashes on login
  - Desktop is narrating keypresses, mouse clicks, or UI elements out loud (screen reader / Orca active)
  - User wants to disable audio narration of the desktop
description: >
  Use when: Broad Wayland desktop session recovery skill covering launch-path tracing, systemd user targets, portal dependencies, and startup-vs-teardown diagnosis.
version: 1.0.0
license: MIT
platforms: [linux]
metadata:
  tags: [wayland, hyprland, gdm, portals, systemd-user, session, troubleshooting]
related_skills:
  - atomic-desktop-app-installation
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

## Capture from a Hermes CLI session (Hyprland / wlroots)

Do not hardcode UID `1000` or `wayland-1`. Use `$XDG_RUNTIME_DIR`, `$WAYLAND_DISPLAY`, and `$UID`.

1. **computer_use / cua-driver** — load `computer-use`. Empty 0×0 captures mean Wayland mode is off (silent X11 fallback).
2. **grim** (if installed; not on Silverblue by default):
   `WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1} XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$UID} grim /tmp/screen.png`
3. **hyprctl dispatch exec** — run grim in the compositor context when it is on the user PATH but not the agent PATH:
   ```bash
   HYPRLAND_INSTANCE_SIGNATURE=$(ls ${XDG_RUNTIME_DIR:-/run/user/$UID}/hypr/ | head -1) \
     hyprctl dispatch exec "grim /tmp/screen.png"
   ```
4. **XDG portal screenshot (gdbus)** — visible confirmation dialog; not for background capture.

CDP attach, Firefox `--remote-debugging-port`, and Kasada/headless screenshots belong in `firecrawl-stealth-fallback` / `computer-use`, not here.

## Orca Screen Reader (audio narration of desktop)

When the user reports that the desktop narrates keypresses, UI elements, or mouse actions out loud,
the cause is almost always the GNOME Orca screen reader running — NOT a Hermes TTS setting.

**Diagnosis:**
```bash
gsettings get org.gnome.desktop.a11y.applications screen-reader-enabled
systemctl --user is-active orca
pgrep -a orca
```
All three should confirm Orca is active.

**Fix (immediate, no reboot needed):**
```bash
gsettings set org.gnome.desktop.a11y.applications screen-reader-enabled false
systemctl --user stop orca
```
Verify with `pgrep orca` — should return nothing.

**Pitfall:** Users often attribute this to Hermes TTS or some other app.
Check Orca first before touching Hermes config or TTS toolset settings.
The `tts` toolset in Hermes only produces audio when explicitly invoked via
the `text_to_speech` tool — it does not narrate general system activity.

## Kitty numpad arrows

Terminal-emulator bindings, not session recovery. Procedure: `references/kitty-numpad-keybinding-fix.md`. GLFW keycodes in that file are kitty-version-specific — re-check after a kitty upgrade.

## Hyprland agent-residue cleanup

Procedure: `references/hyprland-agent-residue-cleanup.md`. Workflow step 4 already covers when to run it.

## Hyprland keybind not firing

Full path: `references/hyprland-keybind-debugging.md`.
This-machine bind file: `~/.config/hypr/UserConfigs/UserKeybinds.conf` (not general Hyprland layout).
Use `${XDG_RUNTIME_DIR:-/run/user/$UID}/hypr/` for logs — do not hardcode UID 1000.
GNOME **keybind** `gsettings` schemas are irrelevant on Hyprland. Orca still uses the GNOME a11y schema (`org.gnome.desktop.a11y.applications`) even under Hyprland — that is not a keybind lookup.


## Notes
More specific workflows that fit under this umbrella include Hyprland/GDM/UWSM session bootstrap, portal dependency recovery, and post-start teardown triage.

References:
- `references/hyprland-session-exit-triggers.md` — teardown-vs-crash triage and safer Hyprland exit wrappers
- `references/hyprland-agent-residue-cleanup.md` — post-migration autostart/unit residue
- `references/hyprland-keybind-debugging.md` — Alt+F4 / bind not firing diagnostic path
- `references/kitty-numpad-keybinding-fix.md` — numpad arrow CSI remap and kitty +runpy introspection
