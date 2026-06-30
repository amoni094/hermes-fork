---
name: waybar-popup-menu-debugging
description: Diagnose and fix Waybar popup menu action wiring and on-screen placement without accidentally moving the toolbar anchor.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [waybar, gtk, hyprland, css, popup-menu, debugging]
---

# Waybar Popup Menu Debugging

Use this for Waybar modules that open a popup menu via `menu`, `menu-file`, and `menu-actions`, especially power menus in Hyprland/Wayland setups.

## When to use
- A Waybar popup opens but its buttons do nothing.
- The popup is offset from the top-right toolbar or screen edge.
- CSS tweaks appear to move the toolbar/module instead of the popup.
- Menu position changes seem inverted, ignored, or clamped.

## Core lessons
1. Separate the popup anchor from the popup itself.
   - `#custom-power` or other module CSS changes move the toolbar/module anchor.
   - `GtkMenu` properties in the `menu-file` affect the popup more directly.
   - If the user asked to move only the dropdown, do not keep changing module margins.

2. Waybar popup actions must match menu item IDs.
   - `menu-actions` should map menu item IDs to commands.
   - On current Waybar versions, prefer an explicit object/map (`{"lock": "...", "shutdown": "..."}`), not a positional array.
   - The IDs in `menu-actions` must match the `GtkMenuItem` IDs in the GtkBuilder XML.
   - If the menu renders but clicks do nothing, inspect this mapping first.
   - A common failure signature in `waybar -l trace` is repeated GTK binding errors immediately after loading the `menu-file`, especially `g_signal_connect_data: assertion 'G_TYPE_CHECK_INSTANCE (instance)' failed`; this strongly suggests Waybar could not bind actions to menu items, often because `menu-actions` was shaped incorrectly.

3. GTK edge handling can override your expectations.
   - When a popup is near the screen edge, GTK/Waybar may clamp or re-anchor it.
   - A requested move "right" can appear to go left/up or barely move at all.
   - Large horizontal offsets near the far-right edge are especially likely to trigger this.

4. CSS `menu { ... }` rules may not control final popup placement reliably.
   - Read back the active CSS, but do not assume `margin-top` / `margin-right` on `menu` are the effective placement controls.
   - If CSS changes appear to have no effect, shift to GtkBuilder properties in the `.ui` file.

## Files to inspect
Typical split:
- `~/.config/waybar/config` or included module files: module declaration and `menu`, `menu-file`, `menu-actions`
- `~/.config/waybar/*.ui`: GtkBuilder definition of the popup menu
- `~/.config/waybar/style.css`: toolbar/module styling and any popup CSS
- action scripts such as `~/.config/hypr/scripts/PowerAction.sh`

## Recommended workflow
1. Read the module config.
   - Confirm which module owns the popup.
   - Confirm whether it truly uses Waybar's built-in popup (`menu = "on-click"`, `menu-file`, `menu-actions`) or whether it launches an external script via `on-click`.
   - Do not assume a nearby `power-menu.ui` file is active just because it exists in the config directory.

2. If the module launches a script, inspect that script before touching GTK assets.
   - Check whether the real menu is provided by rofi, wlogout, bemenu, or another external launcher.
   - For rofi-backed power menus, position and dismissal behavior are controlled by the launcher script and `.rasi` theme, not by Waybar `menu-file` / `GtkMenu` settings.
   - Only continue to GtkBuilder inspection if the module is actually wired to Waybar's built-in menu.
   - For rofi-backed menus, prefer theme-level `x-offset` / `y-offset` for small placement changes, and inspect launcher flags for focus/dismissal behavior.
   - If the user wants click-away dismissal, avoid flags that force standalone window behavior or unusual focus capture.
   - On Hyprland, rofi `click-to-exit` may still fail to dismiss reliably for a toolbar-triggered dmenu even after removing `-normal-window` and `-steal-focus`.
   - If click-away is still broken, next escalate to `-transient-window`, disable `hover-select` in the dedicated power-menu theme, and only keep any active-window watcher as a best-effort fallback rather than the primary fix.
   - If transient rofi still does not dismiss correctly, stop iterating on rofi flags and switch the power menu to a purpose-built alternative such as `wlogout` or another explicitly dismissible launcher.

3. Read the GtkBuilder menu file.
   - Confirm there is an object `class="GtkMenu" id="menu"`.
   - Record the exact `GtkMenuItem` IDs.
   - If present, inspect `margin-right`, `margin-top`, and `halign`.

3. Fix action wiring before position tuning.
   - Ensure `menu-actions` maps each item ID to the actual command or script invocation.
   - Example pattern:
     - `"shutdown": "~/.config/hypr/scripts/PowerAction.sh shutdown"`
     - `"reboot": "~/.config/hypr/scripts/PowerAction.sh reboot"`
   - Re-test after reloading Waybar.

4. Establish a baseline for positioning.
   - Reset experimental offsets before further tuning.
   - Keep toolbar/module anchor adjustments minimal unless the user explicitly wants the toolbar moved.

5. If only the dropdown must move, prefer the `.ui` file.
   - First adjust `GtkMenu` `margin-right` and `margin-top` in the `.ui` file.
   - Use small steps and verify after each change.
   - Expect signs/directions to behave non-intuitively near the screen edge.

6. If changes are ignored or unstable, treat it as edge clamping or per-click re-anchoring.
   - Explain that GTK popup placement may be constrained by screen-edge anchoring.
   - If the user reports the dropdown appears in a different place on different clicks, assume the built-in Waybar/GTK popup is not stable enough for pixel tuning.
   - Avoid repeated large swings in CSS that just move the toolbar.
   - If precise placement is required and built-in placement keeps fighting, replace the built-in Waybar popup with a custom launcher/popup script you can position explicitly.

7. Preferred fallback: replace the built-in menu with a custom launcher.
   - Change the Waybar module from `menu` / `menu-file` / `menu-actions` to a plain `on-click` launcher script.
   - Have the launcher present the power choices in a stable popup tool such as rofi.
   - Dispatch each choice to the existing action script so behavior stays centralized.
   - Position the custom popup with the launcher tool's own coordinates/offsets rather than trying to tune GTK menu margins.
   - This avoids moving the toolbar anchor while giving deterministic placement.

8. Reverse the fallback when the user explicitly wants a true dropdown attached to the Waybar button.
   - If `custom/power` is currently wired to `on-click: PowerMenu.sh` (or another rofi launcher), inspect whether a valid `power-menu.ui` already exists.
   - When repeated rofi focus/click-away tuning fails, stop stacking more rofi flags and switch the module back to Waybar's native popup using `menu: "on-click"`, `menu-file`, and `menu-actions`.
   - Reuse the existing centralized power action script for `menu-actions` so the actions stay consistent.
   - Reload Waybar after rewiring and verify the process is still running.
   - Treat this as the preferred fix when the requirement is specifically "dismiss by clicking away" on a button-anchored dropdown.

## Verification
- Read back the changed files after each edit.
- Reload Waybar (for example via `SIGUSR2`) and confirm the running process still exists.
- Run Waybar with the active config in trace mode to catch menu-file parsing or action-binding errors.
- If clicks do nothing, compare trace logs before/after the change; disappearance of GTK binding errors after `power-menu.ui` loads is good evidence the action wiring is fixed.
- For action failures, prefer config/UI verification first; only test shutdown/reboot scripts carefully and intentionally.

## Pitfalls
- Mistaking module margin changes for popup movement.
- Chasing popup position with large right-edge offsets that trigger GTK re-anchoring.
- Assuming CSS `menu` margins are the authoritative placement mechanism.
- Leaving `menu-actions` as an ordered list when the menu item IDs need explicit mappings.
- Reporting success on placement without user-visible verification.
- Continuing to tune the built-in Waybar/GTK popup after repeated per-click drift or inverted offset behavior; at that point, replace it with a custom launcher (typically rofi) with explicit x/y offsets.
- Moving the toolbar anchor when the user asked to move only the dropdown; once you switch to a custom launcher, keep the toolbar fixed and tune only launcher offsets.
- Leaving power-menu actions as single-path commands that fail silently; route selections through a dedicated action script with fallbacks and desktop notifications on failure.

Reference: see references/waybar-built-in-popup-vs-rofi-power-menu.md for the built-in-popup drift pattern and a working rofi replacement layout.

## Support files
- `references/waybar-popup-menu-notes.md` — condensed notes from a real session on action wiring, edge clamping, anchor-vs-popup behavior, and the custom-launcher fallback when Waybar/GTK popup placement is inconsistent.
- `references/waybar-built-in-popup-vs-rofi-power-menu.md` — built-in-popup drift pattern and a working rofi replacement layout.
- `references/rofi-power-menu-focus-and-offsets.md` — how to recognize a rofi-backed power menu, tune click-away dismissal, and adjust offsets without editing inactive GTK menu files.
- `references/waybar-power-menu-rofi-to-native-reversal.md` — when repeated rofi click-away tuning fails and the correct fix is to rewire `custom/power` back to Waybar's native `menu`/`menu-file`/`menu-actions` popup.

## User-workflow note
For this user, keep changes small and targeted. When they ask to move only the dropdown, avoid shifting the top-right toolbar anchor as a side effect.

## Support files
- `references/waybar-popup-menu-notes.md` — condensed notes from a real session on action wiring, edge clamping, anchor-vs-popup behavior, and the custom-launcher fallback when Waybar/GTK popup placement is inconsistent.
