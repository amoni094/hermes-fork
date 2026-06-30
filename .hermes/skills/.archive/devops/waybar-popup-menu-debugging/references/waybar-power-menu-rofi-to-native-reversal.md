# Waybar power menu: reverse a rofi fallback back to native Waybar popup

Use when:
- the user wants a true dropdown attached to the Waybar power button
- `custom/power` currently launches `PowerMenu.sh` or another rofi script
- repeated rofi tuning (`click-to-exit`, focus flags, transient window, compositor focus watchers) still does not produce reliable click-away dismissal

## Practical pattern
1. Inspect the active module wiring first.
   - If the module uses `on-click` with `PowerMenu.sh`, the active dropdown is not the `power-menu.ui` GTK menu even if that file exists.
2. Check whether `power-menu.ui` is already present and valid.
   - A valid file contains a `GtkMenu` with id `menu` and `GtkMenuItem` ids matching the intended actions.
3. Rewire `custom/power` from launcher mode back to native Waybar menu mode.
   - Replace `on-click` with:
     - `menu: "on-click"`
     - `menu-file: "$HOME/.config/waybar/power-menu.ui"`
     - `menu-actions: [ ... ]`
4. Point `menu-actions` at the centralized power action script rather than duplicating shutdown commands.
   - Example mapping order used successfully:
     - `PowerAction.sh lock`
     - `PowerAction.sh suspend`
     - `PowerAction.sh logout`
     - `PowerAction.sh reboot`
     - `PowerAction.sh shutdown`
5. Reload Waybar and confirm the process survives the reload.

## Why this matters
Rofi is a good fallback when GTK popup placement drifts, but it is the wrong abstraction when the user's core requirement is native dropdown behavior anchored to the button and dismissed by clicking elsewhere.

## Verification pattern
- Read back the module block after editing.
- Syntax-check the shared action script if used by `menu-actions`.
- Reload Waybar (for example `SIGUSR2`) and confirm `pgrep -a waybar` still shows the process.

## Session lesson
Do not keep escalating rofi flags indefinitely for a button-attached dropdown requirement. Once rofi click-away has failed after normal-window/steal-focus removal plus transient/focus-loss workarounds, switch the module back to native Waybar popup wiring if the GTK menu asset already exists.
