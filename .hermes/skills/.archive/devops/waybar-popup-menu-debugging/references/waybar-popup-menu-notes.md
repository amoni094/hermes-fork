# Waybar popup menu notes

Session lessons added:

- If the user reports the dropdown lands in a different place on different clicks, treat the built-in Waybar `GtkMenu` popup as unstable for pixel-perfect positioning.
- CSS `menu { margin-* }` tuning may be ignored or produce misleading results because it is not the final authority for popup placement.
- `GtkMenu` properties in the `.ui` file (`margin-right`, `margin-top`, `halign`) can also behave inverted or inconsistently near the screen edge.
- Repeated attempts to move only the dropdown can accidentally move the toolbar if `#custom-power` or other module CSS is changed; keep anchor and popup changes separate.
- When popup placement is inconsistent across clicks, stop micro-tuning and switch to a deterministic fallback.

Recommended fallback pattern:

1. Keep the existing action script (example: `PowerAction.sh`) as the single dispatch point for lock/suspend/logout/reboot/shutdown.
2. Replace the Waybar module's built-in menu wiring:
   - remove `menu`
   - remove `menu-file`
   - remove `menu-actions`
   - use `on-click` with a launcher script instead
3. In the launcher script, use a stable popup tool such as rofi.
4. Position the popup with the launcher's own placement controls (for rofi, a `-theme-str` override with `location`, `anchor`, `x-offset`, `y-offset`).
5. Map each selected menu label back to the existing action script.

Why this works:

- The launcher popup is no longer tied to Waybar/GTK popup anchoring heuristics.
- The top-right toolbar stays put because you are no longer moving the module anchor to fake popup movement.
- Power actions remain centralized in one script, so the visual/menu layer can change without duplicating shutdown/reboot logic.

Verification pattern:

- Read back the launcher script.
- Read back the Waybar module block to confirm it now uses `on-click` only.
- Syntax-check the launcher script (`bash -n` for shell).
- Reload Waybar and confirm config parsing still succeeds.

Caution:

- Do not claim destructive power actions were verified by execution unless the user explicitly wanted that side effect.
- Verify the wiring and command paths, not the shutdown itself, unless asked.