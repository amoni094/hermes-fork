Waybar power-menu debugging notes from a Hyprland/Silverblue session

Problem pattern
- Built-in Waybar/GTK popup attached to a top-right power module was visually unstable.
- On repeated clicks, the popup did not appear in a consistent location.
- CSS margin tweaks and GtkBuilder margin-top/margin-right changes behaved inconsistently or effectively inverted.
- Moving the anchor module to force the popup right also shifted the whole top-right toolbar, which the user did not want.
- Menu actions appeared wired but clicking shutdown/reboot/etc did nothing reliably.

Durable lesson
- When a Waybar menu popup near the screen edge re-anchors or clamps unpredictably, stop spending cycles on CSS/GtkMenu pixel tuning.
- Treat repeated per-click drift as a signal to replace the built-in Waybar/GTK popup with a custom launcher (rofi/wofi/fuzzel) that has explicit window positioning.
- Keep the Waybar module anchor fixed unless the user explicitly asks to move the toolbar/module itself. Prefer changing only the popup implementation/offsets.

Working replacement pattern
1. Replace Waybar menu/menu-file/menu-actions on the custom module with on-click calling a script.
2. Use a dedicated rofi theme file for the power menu rather than generic theme-str tweaks.
3. Disable input/search UI for power menus.
4. Enable outside-click dismissal.
5. Dispatch the chosen action to a separate PowerAction.sh so menu UI and action logic stay separate.

Rofi flags/theme that helped
- rofi -dmenu -i -no-custom
- -click-to-exit
- -normal-window
- -steal-focus
- Theme settings:
  - window { location: northeast; anchor: northeast; x-offset: ...; y-offset: ...; }
  - mainbox children: [ "listview" ]
  - inputbar, prompt, entry, case-indicator, message { enabled: false; }
  - narrower width and tighter padding reduce empty right-side space

Action-script hardening pattern
- Keep PowerAction.sh as the only executor.
- Use explicit action mapping from menu labels to script args.
- Add fallbacks instead of a single command path:
  - lock: hyprlock -> loginctl lock-session
  - suspend: systemctl suspend -> loginctl suspend
  - logout: uwsm stop -> hyprctl dispatch exit 0
  - reboot: systemctl reboot -> loginctl reboot
  - shutdown: systemctl poweroff -> loginctl poweroff
- Show a desktop notification on failure so the user does not see a silent no-op.

User-workflow lesson
- If the user says 'only adjust the dropdown position', do not alter module margins/anchor values that move the whole toolbar.
- Once the popup is custom/rofi-backed, tune only x-offset/y-offset in the rofi theme for predictable iteration.