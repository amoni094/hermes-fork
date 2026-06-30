# Hyprland + GDM + systemd-user notes

Condensed lessons from a Fedora 44 Silverblue investigation where Hyprland failed to establish a usable graphical user session.

## Durable findings

- `graphical-session.target` must be inspected as a unit definition, not treated as a generic startable target.
- If `systemctl --user cat graphical-session.target` shows `RefuseManualStart=yes`, a compositor `exec-once` line that runs `systemctl --user start graphical-session.target` is invalid and should be removed.
- `xdg-desktop-portal.service` can fail as a downstream symptom when it has `Requisite=graphical-session.target` and that target is inactive.
- A session can appear to reach Hyprland briefly and still be fundamentally broken because the systemd user graphical session was never established correctly.
- When both a plain session entry and a UWSM-managed session entry exist, the managed path is the correct next check before adding more compositor startup hacks.

## Specific evidence pattern to look for

This combination is highly suggestive of a session-manager integration failure rather than a pure portal bug:

- previous-boot journal shows GDM auth and Hyprland launcher start
- portal logs report `Current graphical user session is inactive`
- `xdg-desktop-portal.service` fails with `dependency`
- compositor launcher aborts later with a message like `Resource deadlock avoided`

## Fedora/GDM session-entry pattern

Useful comparison:

- `hyprland.desktop` -> plain launcher such as `/usr/bin/start-hyprland`
- `hyprland-uwsm.desktop` -> `uwsm start ...`

If the managed entry exists but `uwsm` itself is missing, verify package availability first, then consider a source install.

## Source-build note for UWSM

A workable fallback on Fedora Atomic when no native package is available:

1. clone upstream UWSM
2. install `meson` and `ninja` in user space if missing
3. run Meson configure
4. if Meson errors on missing `scdoc`, retry with `-Dman-pages=disabled`
5. install to `/usr/local` with sudo

This is not a guarantee that the login issue is solved, but it is a valid way to make the managed desktop entry runnable when the binary is absent.
