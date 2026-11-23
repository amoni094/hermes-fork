# Hyprland GUI helper gap on Fedora Atomic / Silverblue

Use this when Hyprland is running but a menu, quick-settings panel, or dotfile script says GUI utilities are not enabled, missing, or unavailable.

## High-yield distinction

This message often means optional helper applications are absent, not that the Wayland session failed.

Confirm the distinction in this order:

1. Session health
   - `XDG_CURRENT_DESKTOP`
   - `DESKTOP_SESSION`
   - `graphical-session.target`
   - `xdg-desktop-portal.service`
   - `xdg-desktop-portal-hyprland.service`
2. Script origin
   - Read the launcher or quick-settings script that emitted the message.
   - Look for `command -v`, `which`, or package-presence checks.
3. Binary presence
   - Check the exact helper names on `PATH`.
4. Package source
   - On Fedora Atomic, prefer `rpm-ostree` verification and COPR repo enablement where needed.

## Common Hyprland helper apps

In Hyprland dotfile packs, the missing utilities are often:
- `nwg-displays`
- `nwg-look`
- `qt5ct`
- `qt6ct`

These are optional GUI helpers for display/layout and theme settings. Their absence does not by itself mean Hyprland, UWSM, or portals are broken.

## Atomic-specific handling

- Prefer a small host-package fix over rerunning the whole installer.
- If a helper comes from COPR, capture the exact repo enablement step.
- If sudo is required and unavailable to the agent, stop at a verified install command and say the host change is pending user authentication.

## Example outcome pattern

Healthy:
- `XDG_CURRENT_DESKTOP=Hyprland`
- `DESKTOP_SESSION=hyprland-uwsm`
- `graphical-session.target` active
- portal services active

Missing helpers:
- helper binaries absent from `PATH`
- quick-settings script contains explicit checks and fallback notifications

Interpretation:
- session is up
- optional GUI helper packages are missing
- next action is package installation, not compositor surgery
