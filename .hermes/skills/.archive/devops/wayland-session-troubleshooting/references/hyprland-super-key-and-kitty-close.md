# Hyprland super-key launcher vs direct special-workspace toggle

Use this when a Hyprland setup appears to bind the Super/Windows key to one thing, but the observed behavior comes from a helper script instead of a direct dispatcher.

## Symptom shape

- Double-tapping the Windows key opens an overview or selector instead of going directly to a special workspace.
- `ALT+F4` is bound to `killactive`, but terminal windows still ask for close confirmation.

## High-yield checks

1. Read the sourced root config first to confirm whether `UserConfigs/UserKeybinds.conf` is loaded after the defaults.
2. Inspect the live bind and the helper script it calls.
   - A bind like:
     - `bindr = $mainMod, SUPER_L, exec, $scriptsDir/SuperLauncher.sh`
   means the real behavior lives in `SuperLauncher.sh`, not in the bind line itself.
3. For double-tap behaviors, inspect timing/state files in the helper script before changing workspace binds elsewhere.
4. If the user wants the double-tap action to go straight somewhere, do not assume the overview/selector is acceptable just because it exposes the target.
   - Ask what “desktop” means in that setup: a special workspace, an overview tile, or an empty normal workspace.
5. If the user wants direct special-workspace entry, change the double-tap path to dispatch Hyprland directly:
   - `hyprctl dispatch togglespecialworkspace`
   instead of launching an overview script.
6. If the user says the overview opens a screen like “Special workspace” and they must then choose Desktop, bypass the overview entirely.
   - Prefer a direct helper that switches to the first empty normal workspace, which behaves like “go to desktop” in many Hyprland setups.
   - A durable pattern is: inspect `hyprctl workspaces -j`, find the first workspace with `windows == 0`, and dispatch `hyprctl dispatch workspace <id>`.
   - If all common workspaces are occupied, choose the next numeric workspace.
7. If `ALT+F4` already maps to `killactive` but terminal windows still prompt, inspect the terminal emulator config.
   - For Kitty, disable OS-window close confirmation with:
     - `confirm_os_window_close 0`

## Verification pattern

- `bash -n ~/.config/hypr/scripts/SuperLauncher.sh`
- `Hyprland --verify-config -c ~/.config/hypr/hyprland.conf`
- Read back `~/.config/kitty/kitty.conf` to confirm `confirm_os_window_close 0`
- Optionally live-check the dispatcher with `hyprctl dispatch togglespecialworkspace`

## Pitfalls

- Do not assume the keybind line is the full source of truth when it launches a wrapper script.
- Do not keep debugging Hyprland close bindings if the confirmation is coming from the terminal emulator itself.
- Do not declare the fix complete without verifying both the compositor config and the helper script syntax.