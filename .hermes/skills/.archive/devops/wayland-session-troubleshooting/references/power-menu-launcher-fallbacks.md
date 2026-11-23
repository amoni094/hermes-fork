# Power menu launcher fallbacks on Hyprland

Use this when a tray/Waybar/panel power icon appears dead even though the session itself is healthy.

## High-yield checks

1. Read the click action from the panel config first.
   - Common patterns point to wrapper scripts such as `~/.config/hypr/scripts/Wlogout.sh`.
2. Verify the wrapper script exists and is executable.
3. Syntax-check the script with `bash -n`.
4. Check whether the script's primary launcher binary actually exists.
   - Example: `command -v wlogout`
5. If the primary launcher is missing but another menu launcher exists, prefer a graceful fallback instead of leaving the click action broken.
   - Example fallback: use `rofi -dmenu` to present Lock / Suspend / Log out / Reboot / Shut down.
6. Verify by launching the wrapper script directly and confirming the fallback process appears.

## Durable pattern

For user-facing launcher scripts, prefer this structure:

- keep the preferred native launcher when available (`wlogout`)
- gate it with `command -v ...`
- provide a small fallback using a binary already present on the system (`rofi`, `wofi`, `fuzzel`, etc.)
- keep shutdown/reboot/logout actions inside the wrapper so the panel config does not need to change
- when the fallback is launched from a top-bar button, style it like a dropdown anchored to that corner instead of a centered modal so the interaction still feels native to the panel

### Wayland dismissal pitfall

If the user specifically wants click-away dismissal from a panel-anchored power menu, prefer `wlogout` first when it is installed and already configured. In this session, a `rofi -dmenu` fallback still failed the click-away requirement even after trying `click-to-exit`, `-no-steal-focus`, and `-transient-window`. Capture the launcher as:

- `wlogout` first when present
- `rofi` only as a fallback when `wlogout` is absent

This keeps the Waybar/Hyprland power button on the native path and avoids spending extra turns trying to coerce popup-dismiss semantics out of the fallback launcher.

## Themed rofi dropdown pattern

When `rofi` is the fallback for a bar power button:

1. Put the layout in a dedicated theme file such as `~/.config/rofi/config-power-menu.rasi`.
2. Import the existing palette/theme source first so the fallback inherits the current desktop look.
   - Example: a wallust-generated `colors-rofi.rasi` import.
3. Use corner anchoring rather than centered placement.
   - Typical pattern for a top-right Waybar button:
     - `location: northeast;`
     - `anchor: northeast;`
     - small positive `y-offset` to drop below the bar
     - `x-offset: 0px` or a tiny correction only if visual alignment needs it
4. Keep the menu compact.
   - narrow width
   - limited lines matching the number of actions
   - bottom-rounded corners if the menu should appear to emerge from the bar edge
5. Verify both pieces separately:
   - `bash -n` on the wrapper script
   - `rofi -no-config -theme <theme> -dump-theme` on the theme file
6. Launch the wrapper directly once to confirm the fallback menu actually appears with the intended geometry.

## Example symptom shape

- Waybar power icon bound to `~/.config/hypr/scripts/Wlogout.sh`
- `wlogout` missing from PATH
- click appears to do nothing
- script patched to fall back to `rofi -dmenu`
- direct launch confirms a `rofi` power menu process appears
