# Hyprland session-exit triggers: teardown vs crash

Use this note when a Wayland desktop "randomly logs out" and user services like Hermes die with it.

## Fast triage
If the stop window shows all of the following, classify it as session teardown first:
- `uwsm` receives `SIGTERM`
- `Stopped target graphical-session.target`
- `Stopped wayland-wm@...service`
- `Activating special unit exit.target`
- broad stop of unrelated user services in the same window

That pattern is not a narrow app crash.

## High-risk trigger classes to audit
Check user-facing exit paths before editing compositor internals:
- Hyprland keybinds that run `hyprctl dispatch exit` or `hyprctl dispatch exit 0`
- Waybar modules/buttons wired to direct exit commands
- Power dropdowns whose "Log out" action directly calls `hyprctl dispatch exit`
- UWSM wrappers that bypass the normal power-menu path

## Safer fix pattern
- Replace direct exit keybinds/buttons with a power-menu launcher.
- Route the explicit logout action through a wrapper script rather than duplicating raw `hyprctl dispatch exit` in several places.
- After patching, reload the compositor/UI and verify:
  - config points to the wrapper/menu
  - opening the menu does not trigger `exit.target`
  - long-lived user services (for example Hermes gateway/dashboard) stay active when the menu is merely opened

## Example class of change
- `CTRL+ALT+Delete` changed from direct `hyprctl dispatch exit 0` to launching the power menu
- Waybar `custom/quit` changed from direct exit to the same launcher
- power dropdown `Log out` changed from direct exit to a wrapper script
