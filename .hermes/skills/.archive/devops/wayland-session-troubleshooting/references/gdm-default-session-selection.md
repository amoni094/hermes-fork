# GDM default session selection on Fedora

When logs suggest a compositor "failed after reboot", first verify whether GDM actually launched that compositor.

## Fast checks

- Inspect the active desktop variables in the current session:
  - `XDG_CURRENT_DESKTOP`
  - `DESKTOP_SESSION`
  - `GDMSESSION`
- Check whether the user is really in the expected desktop session versus a manager-only user session.
- Inspect `/var/lib/AccountsService/users/<username>`.

Example durable finding from this session:
- `/var/lib/AccountsService/users/rainbow` controlled the default GDM session.
- It was set to `Session=gnome`, so reboot/login returned to GNOME even though the UWSM-managed Hyprland path existed and had already been shown working on the previous boot.
- Setting `Session=hyprland-uwsm` aligned GDM's default with the intended managed Hyprland entry.

## Why this matters

A session-selection mistake can look like a compositor regression:
- previous boot logs may show Hyprland/UWSM and portals working correctly
- current boot may show only GNOME session variables
- the real fix is to correct GDM's default session, not to change compositor startup config again

## Use in future troubleshooting

Before changing Hyprland config or portal units again:
1. compare previous-boot and current-boot launch paths
2. confirm which desktop entry GDM actually selected
3. inspect AccountsService user session defaults
4. only then continue compositor-specific debugging if the intended session was actually launched
