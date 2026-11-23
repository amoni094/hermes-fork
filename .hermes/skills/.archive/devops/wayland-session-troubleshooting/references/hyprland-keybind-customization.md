# Hyprland keybind customization

Use this when the user wants a small shortcut change without broader session surgery.

## Preferred edit surface

- Prefer `~/.config/hypr/UserConfigs/UserKeybinds.conf` when the root `hyprland.conf` already sources it.
- Keep vendor/default keybind packs intact unless there is a good reason to edit them directly.

## Fast path

1. Read `~/.config/hypr/hyprland.conf` first and confirm the keybind source order.
2. Read both the default keybind file and the user keybind override file.
3. Add new shortcuts in the user file.
4. If overriding an existing default shortcut, unbind it first in the user file.
5. Run:
   `Hyprland --verify-config -c ~/.config/hypr/hyprland.conf`
6. Only after verification passes, reload the live session with:
   `hyprctl reload`

## Syntax pitfall

Hyprland bind forms are not interchangeable.

- `bindd` can carry a human-readable description field before the dispatcher/action.
- `bindr` may reject that extra description token and require the simpler form:
  `bindr = $mainMod, SUPER_L, exec, pkill rofi || true && rofi -show drun -modi drun,filebrowser,run,window`

If `Hyprland --verify-config` reports `Invalid dispatcher` after adding a `bindr` line, remove the description token first before assuming the command itself is wrong.

## Example from this session

Goal:
- Super key alone opens the app selector
- Ctrl+Alt+T opens the configured terminal

Working user-file entries:

```conf
# Launch app selector with the Windows key alone
bindr = $mainMod, SUPER_L, exec, pkill rofi || true && rofi -show drun -modi drun,filebrowser,run,window

# Open terminal with Ctrl+Alt+T
bindd = CTRL ALT, T, open terminal, exec, $term
```

## Verification standard

Do not claim the shortcut is configured until both are true:
- `Hyprland --verify-config` returns `config ok`
- `hyprctl reload` succeeds in a live session
