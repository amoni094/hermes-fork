# Hyprland post-start teardown triage

Use this when Hyprland appears to start, then the session dies or returns to GDM almost immediately.

## Pattern that means "not a startup crash"

If the journal shows all or most of the following in order:
- compositor selected by GDM/UWSM
- Hyprland startup banner or other compositor success marker
- `Reached target wayland-session@...target`
- `Reached target graphical-session.target`
- portal backend started
- then `Stopped target graphical-session.target`
- then `Received SIGTERM, stopping wayland-session-envelope@...target`
- then `Reached target shutdown.target` and/or `Stopping user@<uid>.service`

Treat the incident as a teardown trigger investigation, not a compositor boot failure.

## High-yield places to inspect

1. Hyprland keybinds
- `hyprctl dispatch exit 0`
- `systemctl suspend`
- power-menu launchers
- hardware-key bindings such as `XF86Sleep`

2. Wlogout or equivalent power-menu configuration
- `systemctl reboot`
- `systemctl poweroff`
- `hyprctl dispatch exit 0`
- suspend / hibernate actions

3. Waybar or panel click handlers
- custom reboot button
- custom quit/exit button
- power-menu launch button

4. User services and helpers
- separate lock-only actions (`loginctl lock-session`, `loginctl lock-sessions`) from real teardown actions
- lid helpers may lock the session without causing shutdown

## Example durable lesson

In this Fedora/Hyprland/GDM/UWSM investigation, Hyprland reached its session targets successfully. The teardown clue was the immediate transition into `shutdown.target` and user-manager shutdown. The config then showed explicit exit/reboot paths in Hyprland keybinds, wlogout layout, and Waybar actions. A noisy lid-lock helper existed, but it only called `loginctl lock-sessions` and was therefore not a shutdown root cause.

## Reminder

A suspicious numeric string near the same time window may be unrelated. Verify whether it is a real error code or an app/runtime value such as a forwarded port before building the theory around it.
