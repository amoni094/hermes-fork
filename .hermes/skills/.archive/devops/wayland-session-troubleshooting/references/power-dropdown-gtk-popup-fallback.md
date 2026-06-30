# Hyprland power dropdown: GTK popup fallback when rofi click-away fails

Use this when all of the following are true:
- the power button is launched from a stable wrapper script (for example a Waybar on-click target)
- the user wants a compact dropdown, not a full-screen logout overlay
- `rofi` was made parseable and styled correctly but still does not dismiss reliably on outside click under Wayland/Hyprland

## Durable lesson

Treat repeated `rofi` flag/theme tweaks as exhausted once live testing has already covered:
- `-click-to-exit`
- no-steal-focus / removed `-steal-focus`
- removed `-normal-window`
- theme-level `click-to-exit: true` and `steal-focus: false`

If outside-click dismissal still fails after that, the durable move is to replace the launcher implementation, not to keep guessing more `rofi` combinations.

## Recommended fallback shape

Keep the existing click target stable and swap only the wrapper payload.

Example pattern:
- Waybar/Hyprland button still calls `~/.config/hypr/scripts/Wlogout.sh`
- `Wlogout.sh` becomes a thin launcher for a popup script such as `PowerDropdown.py`
- the popup script renders a small top-right menu with the same action labels

## High-value popup properties

- popup-type window instead of a normal desktop window
- singleton behavior via a PID file so repeated clicks close/replace the previous instance
- close on focus-out
- close on `Escape`
- top-right anchoring near the bar power button using compositor monitor geometry (`hyprctl monitors -j`)
- action list kept explicit in one place (Lock, Suspend, Log out, Reboot, Shut down)
- toolbar-matching CSS/theme values passed directly in the popup implementation

## Practical implementation notes

- PyGObject/GTK is a good fit when available locally because it can create a real popup that obeys focus-loss dismissal better than `rofi` in this failure mode.
- Require GI namespaces explicitly before import order becomes ambiguous. For GTK 3-style code, call both:
  - `gi.require_version('Gdk', '3.0')`
  - `gi.require_version('Gtk', '3.0')`
  before importing from `gi.repository`.
- Keep the shell wrapper minimal so the Waybar/Hyprland binding does not need to change again.
- Verify both pieces separately after editing:
  - `python3 -m py_compile ~/.config/hypr/scripts/PowerDropdown.py`
  - `bash -n ~/.config/hypr/scripts/Wlogout.sh`

## Why this belongs in the fallback ladder

The ordering is:
1. native `wlogout` when a full-screen logout layer is acceptable
2. themed `rofi` dropdown when compactness matters and click-away works on this setup
3. custom GTK popup when the user insists on a compact dropdown and live testing shows `rofi` will not dismiss correctly on outside click

Do not claim the GTK fallback is needed before live-testing the simpler `rofi` path; the durable lesson is the pivot threshold, not "always use GTK".
