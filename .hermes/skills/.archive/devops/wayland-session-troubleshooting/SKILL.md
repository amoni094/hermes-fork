---
name: wayland-session-troubleshooting
description: Diagnose Wayland desktop session startup failures on Linux by tracing session-manager integration, systemd user targets, portal dependencies, and compositor launch paths before changing config.
---

# Wayland Session Troubleshooting

Use this when a Linux desktop session (especially Hyprland or other wlroots compositors) starts incompletely, returns to the greeter, loses portal-dependent apps, or shows `xdg-desktop-portal`, `graphical-session.target`, or compositor-launch errors.

This skill is especially useful for Fedora/GDM setups where a compositor can be launched either through a plain desktop entry or a session manager such as UWSM.

## Goals

- Find the real failure edge from logs rather than editing startup config blindly.
- Distinguish compositor crashes from session-manager / systemd-user integration failures.
- Verify whether portal breakage is a root cause or a downstream symptom.
- Prefer proper session management over `exec-once` workarounds.

## Core principle

If `graphical-session.target` or related user-session targets are inactive, treat that as a session-management problem first, not something to brute-force from compositor config.

Do not assume a compositor config line can legitimately start a systemd session target. Check the target unit first.

## Phase 1: establish the launch path

1. Identify which session desktop entry is actually being used.
   - Check `/usr/share/wayland-sessions/*.desktop`.
   - Compare plain compositor entries with managed entries (for example `hyprland.desktop` vs `hyprland-uwsm.desktop`).
2. Read the `Exec=` and `TryExec=` lines.
3. Verify whether the manager binary exists.
   - Example: `uwsm` may be referenced by a desktop entry but not installed.
4. Confirm package ownership of the session files so you know whether they came from the compositor package or local customizations.
5. On GDM systems, verify the user's default session selection.
   - Check current session variables such as `XDG_CURRENT_DESKTOP`, `DESKTOP_SESSION`, and `GDMSESSION`.
   - Inspect `/var/lib/AccountsService/users/<username>` for the persisted `Session=` value.
   - Treat a mismatch here as a launch-selection problem before changing compositor config.

## Phase 2: verify systemd user session state

1. Inspect the relevant user units:
   - `graphical-session.target`
   - `graphical-session-pre.target`
   - `xdg-desktop-portal.service`
   - compositor-specific portal backends such as `xdg-desktop-portal-hyprland.service`
2. Read unit definitions, not just status.
3. Specifically check for:
   - `RefuseManualStart=yes`
   - `PartOf=`
   - `Requisite=`
   - `After=`
   - environment conditions such as `WAYLAND_DISPLAY`
4. If the target is marked `RefuseManualStart=yes`, stop trying to start it from compositor config; that is not a valid fix path.

## Phase 3: correlate logs around one failed boot

1. Use a single boot window and reconstruct the sequence:
   - GDM authentication
   - session launcher start
   - compositor greeting / first success marker
   - portal dependency failures
   - teardown or abort
2. Prefer targeted previous-boot journal inspection over huge undifferentiated log dumps.
3. Look for ordering clues such as:
   - `graphical-session.target` inactive
   - `xdg-desktop-portal.service` failed with `dependency`
   - compositor launcher aborts such as `Resource deadlock avoided`
4. If a previous theory involved GNOME-to-Hyprland transition races, verify on a clean reboot directly into the compositor before keeping that theory.

## Phase 3.5: distinguish startup failure from post-start teardown

If the compositor prints a normal startup banner, `wayland-session@...target` is reached, and `graphical-session.target` becomes active, do not keep treating the case as a startup crash.

Instead, inspect whether the session was explicitly torn down immediately after launch.

1. Search the same boot for teardown markers:
   - `Stopped target graphical-session.target`
   - `Received SIGTERM, stopping wayland-session-envelope@...target`
   - `Reached target shutdown.target`
   - `Stopping user@<uid>.service`
   - `Stopping gdm.service`
2. If those appear right after successful compositor startup, shift from compositor debugging to trigger hunting.
3. Read user-facing session controls and power bindings before changing compositor internals:
   - Hyprland keybinds such as `hyprctl dispatch exit 0`
   - power-menu wrappers such as `wlogout`
   - status-bar click actions such as Waybar `on-click` reboot/quit handlers
   - lid-close or lock helpers launched as user services
   - hardware keys such as `XF86Sleep`
4. Separate lock-only helpers from real teardown actions. A service that calls `loginctl lock-session` or `loginctl lock-sessions` can be noisy without being the root cause of shutdown or logout.
5. Treat unexplained numeric strings carefully. Verify in logs whether they are actual compositor/session errors or unrelated application/runtime values before building a theory around them.

## Phase 4: choose the fix path

### If the plain compositor session does not establish the graphical user session
Prefer the managed session path.

For Hyprland on Fedora/GDM:
- If `hyprland.desktop` launches `/usr/bin/start-hyprland` and `hyprland-uwsm.desktop` launches `uwsm ...`, favor the UWSM-managed session when portal/session targets never become active on the plain path.

### If the manager is not installed
1. Check native package availability first.
2. On Fedora Atomic / Silverblue, verify with the host package workflow before assuming it is packaged.
3. If the package is unavailable, use a source-install fallback only after confirming the managed desktop entry already expects that binary.

### If the session is healthy but the desktop says GUI utilities are not enabled
Treat this as a helper-binary/package gap before treating it as a portal or compositor failure.

1. Verify the session is actually healthy first:
   - `XDG_CURRENT_DESKTOP`, `DESKTOP_SESSION`
   - `graphical-session.target`
   - `xdg-desktop-portal.service`
   - compositor-specific portal backend such as `xdg-desktop-portal-hyprland.service`
2. Read the compositor helper scripts and menus that produced the message.
   - For Hyprland dotfile packs, inspect launchers such as quick-settings scripts before changing core session config.
3. Check whether the expected GUI helper binaries actually exist on `PATH`.
4. If the missing items are helper apps like `nwg-displays`, `nwg-look`, `qt5ct`, or `qt6ct`, explain that the session can be fully up while optional GUI tooling is still absent.
5. For tray/Waybar launchers, verify both the helper binary and the wrapper script behavior before treating the problem as a compositor failure.
   - A common failure shape is a wrapper script that runs a helper which is absent from `PATH`, surfacing as a dead click target rather than a visible error.
   - Check whether the expected launcher binary is actually installed before changing compositor/session internals.
   - For `nmtui` launchers, verify both the helper binary and the terminal invocation.
   - A wrapper script that runs `$term nmtui` can surface as a vague child-launch failure instead of a clean `command not found`.
   - If `nmtui` is missing but `nm-connection-editor` exists, prefer a graceful fallback to `nm-connection-editor` rather than leaving the click action broken.
   - For power-menu launchers, if `wlogout` is missing but `rofi` exists, prefer a wrapper-script fallback to a small `rofi -dmenu` power menu rather than leaving the panel button inert.
   - If the user specifically wants a dropdown that dismisses on outside click under Hyprland/Wayland, do not keep iterating on `rofi` flags once `-click-to-exit`, no-steal-focus, and theme-level focus settings still fail in live testing. Pivot to a real popup implementation (for example a small GTK popup/dropdown window) instead of repeatedly restyling `rofi` or falling back to full-screen `wlogout`.
   - For a custom popup replacement, keep the wrapper path stable (for example leave the Waybar/Hyprland click target invoking the same script) and swap only the launcher payload. Useful properties: singleton behavior so repeated clicks toggle/replace the instance, focus-out dismissal, Esc dismissal, top-right anchoring near the Waybar power button, and direct action dispatch for Lock/Suspend/Log out/Reboot/Shut down.
   - When launching TUIs from Kitty, prefer `kitty -e <cmd>`; other terminals may need their own explicit exec flag rather than bare `$term <cmd>`.
6. On Fedora Atomic / Silverblue, prefer `rpm-ostree` plus any required COPR enablement over ad-hoc mutable-system installer scripts.
7. If sudo is required and unavailable to the agent, stop at the verified install command rather than pretending the fix was completed.

## Fedora Atomic / Silverblue notes

- Prefer small reversible changes and avoid mutating layered packages unless needed.
- For session-manager debugging, user config edits are lower risk than host package changes, but do not keep invalid `systemctl --user start graphical-session.target` workarounds once you confirm the target refuses manual start.
- If a needed helper is absent from current repos, a `/usr/local` source install can be an acceptable fallback when the desktop entry already references that helper.

## UWSM source-build fallback

If UWSM is not available from Fedora repos:

1. Clone the upstream repository.
2. Install build tools in user space if needed.
3. Configure with Meson.
4. If the build fails on missing `scdoc`, retry with man pages disabled.
5. Install to `/usr/local` with sudo.
6. Reboot and choose the managed session entry from GDM.

Example durable lesson from this session:
- Upstream UWSM configured and built successfully with Meson after disabling man pages because `scdoc` was missing.

## Pitfalls

- Do not read a message like "GUI utilities not enabled" as proof that Hyprland, UWSM, or portals are broken; verify whether it is only a helper app launcher complaining about absent binaries.
- Do not jump straight to reinstalling the whole dotfile pack when the session is already healthy and only optional GUI helpers are missing.
- Do not force-start `xdg-desktop-portal` from compositor startup to paper over inactive session targets.
- Do not tell the user to keep a manual `graphical-session.target` startup line after confirming `RefuseManualStart=yes`.
- Do not blame portals first when portal failures are downstream of an inactive graphical session target.
- Do not conclude a GNOME handoff race unless a clean reboot-direct-to-compositor attempt reproduces differently.
- Do not stop at “UWSM desktop entry exists”; verify whether the `uwsm` binary is actually installed.
- Do not assume Hyprland bind syntaxes all take the same fields. In particular, `bindd` supports a description field for searchable keybind menus, but `bindr` may need the plain `bindr = MODS, KEY, exec, ...` form without an extra description token.

- Do not stop at compositor startup success markers; if `graphical-session.target` came up and the journal then entered `shutdown.target`, inspect explicit logout/reboot bindings and autostart actions before changing compositor internals.
- Do not assume a reported numeric "error code" belongs to Hyprland; confirm whether it is actually a port number, app-specific value, or unrelated runtime artifact.

## Small config-change verification pattern

For Hyprland shortcut customization and similar low-risk config edits:

1. Prefer user override files such as `~/.config/hypr/UserConfigs/UserKeybinds.conf` over editing upstream-ish default packs directly.
2. Read the sourced root config first to confirm load order and whether the user override file is already included.
3. If replacing an existing shortcut, unbind the original in the user file before re-binding it.
4. After editing, run `Hyprland --verify-config -c ~/.config/hypr/hyprland.conf` before reloading.
5. If a live session exists, apply `hyprctl reload` only after config verification passes.

Reference: `references/hyprland-keybind-customization.md`.
Additional reference: `references/waybar-network-launcher-fallbacks.md`.
Additional reference: `references/power-menu-launcher-fallbacks.md` — includes the themed `rofi` dropdown fallback pattern for dead Waybar/Hyprland power buttons when `wlogout` is absent, and a `wlogout`-first rule when click-away dismissal is a hard requirement under Wayland.
Additional reference: `references/waybar-power-dropdowns.md` — use Waybar's built-in `menu` / `menu-file` / `menu-actions` on custom modules when the user wants a true bar-anchored dropdown rather than a manually positioned popup.
Additional reference: `references/power-dropdown-gtk-popup-fallback.md` — GTK popup/dropdown replacement pattern for Hyprland/Wayland when the user wants a compact dropdown and `rofi` still refuses to dismiss on outside click after live testing.
Additional reference: `references/hyprland-super-key-and-kitty-close.md` — shortcut-customization pattern when the Super key behavior is mediated by a wrapper script, including when “go to desktop” should bypass an overview and jump straight to an empty workspace, and when `ALT+F4` confirmation comes from Kitty rather than Hyprland.

## Verification checklist

Before declaring the issue fixed:

1. Verify the manager binary exists on disk.
2. Verify the managed `.desktop` entry points to that binary.
3. Re-read any compositor startup config you changed and remove invalid workaround lines.
4. On next failed boot, verify whether `graphical-session.target` becomes active in the managed session.
5. Confirm portal units no longer fail due to `dependency` on inactive session targets.
6. If the reported symptom was a desktop helper or “GUI utilities” gap, verify the helper binaries on the live boot rather than trusting a staged deployment alone.
7. When the compositor and portal stack are healthy again, explicitly restore any temporary safe-debug changes you made to keybinds, power menu bindings, Waybar actions, or sleep keys, then re-run compositor config validation.

## Exiting temporary safe-debug mode

If you neutralized logout, reboot, quit, powermenu, or suspend actions during debugging, treat restoration as part of the fix rather than as optional cleanup.

1. Re-check that the current boot is genuinely healthy first:
   - correct managed session selected
   - `graphical-session.target` active
   - portal backend active
   - compositor config validation passing
2. Restore only the temporary debug-neutralized controls.
   - Examples: Hyprland keybinds for `hyprctl dispatch exit`, `Wlogout.sh`, `systemctl suspend`
   - Waybar buttons that were temporarily replaced with `notify-send` stubs
3. Read the edited files back to confirm the original actions are present again.
4. Re-run compositor config validation after the restoration.
5. Only then declare debugging mode exited.

## References

- `references/hyprland-gui-helper-gap-fedora-atomic.md` — triage pattern for Hyprland sessions that are up but missing optional GUI helper utilities on Fedora Atomic/Silverblue.
- `references/hyprland-post-start-teardown-triage.md` — post-start teardown pattern for Hyprland/GDM/UWSM sessions, with high-yield checks for keybind, wlogout, Waybar, and lock-helper triggers.
