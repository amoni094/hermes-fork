# Hyprland Keybind Not Firing — Diagnostic Path

## Context
User: Alt+F4 defined in Hyprland config but does nothing when pressed in Firefox or a non-active terminal.

## Key facts established before session ended
- Session type: `wayland`, DESKTOP_SESSION: `hyprland-uwsm`
- `gsettings` GNOME keybinds are **irrelevant** on Hyprland — always check `hyprctl binds`, not gsettings
- Binding was correctly defined in `~/.config/hypr/UserConfigs/UserKeybinds.conf`:
  `bindd = ALT, F4, close focused window, killactive,`
- `hyprctl binds -j` confirmed it loaded: modmask=8 (Alt/Mod1), key=F4, dispatcher=killactive, locked=false
- `hyprctl dispatch killactive` works directly — so the dispatcher itself is fine
- No key remappers running (keyd, kanata, xremap, ydotool, wev, kmonad, input-remapper)
- No Hyprland submap active (`hyprctl submap` → `default`)
- Kitty has no internal Alt+F4 binding conflicting (`~/.config/kitty/` clean)

## Key open question at session end
Enable debug logging and check whether Hyprland sees the keypress at all:
```bash
hyprctl keyword debug:disable_logs false
hyprctl keyword debug:enable_stdout_logs true
# User presses Alt+F4 in target window
tail -n 100 /run/user/1000/hypr/$(ls /run/user/1000/hypr/ | head -1)/hyprland.log | grep -i "f4\|keybind\|modmask\|killactive"
```

## Diagnostic commands (run in order)

### 1. Confirm it's Hyprland, not GNOME
```bash
echo $XDG_SESSION_TYPE   # expect: wayland
echo $DESKTOP_SESSION    # expect: hyprland or hyprland-uwsm
```

### 2. Check binding is loaded
```bash
hyprctl binds -j | python3 -c "
import json, sys
for b in json.load(sys.stdin):
    if b.get('key','').upper() == 'F4':
        print(b)
"
# Key fields: modmask (8=Alt), dispatcher=killactive, locked, key=F4
```

### 3. Check for competing binds on same key
```bash
hyprctl binds | grep -i "f4"   # should show only one entry
```

### 4. Check no input remappers running
```bash
ps aux | grep -E "keyd|kanata|xremap|ydotool|wev|intercept|kmonad|input-remapper" | grep -v grep
```

### 5. Check no active submap
```bash
hyprctl submap   # expect: default
```

### 6. Test dispatcher directly
```bash
hyprctl dispatch killactive   # if this works, problem is key routing, not dispatcher
```

### 7. Enable Hyprland debug logging, press the key, check log
```bash
hyprctl keyword debug:disable_logs false
hyprctl keyword debug:enable_stdout_logs true
# ... press Alt+F4 ...
LOGFILE=/run/user/1000/hypr/$(ls /run/user/1000/hypr/ | head -1)/hyprland.log
tail -200 "$LOGFILE" | grep -i "f4\|keybind\|modmask\|killactive\|key press"
```

## Suspected root cause (unconfirmed at session end)
`locked: false` on the bind + possible modifier mismatch from NumLock/CapsLock state.
On some Hyprland versions, extra active modifiers (NumLock adds modmask 16) cause the bind's
modmask to not match the pressed key's full modifier mask, silently failing the bind lookup.

### Fix to try if log shows key seen but bind not matched:
Add NumLock-ignore flag. In config:
```
bindd = ALT, F4, close focused window, killactive,
```
Hyprland should ignore NumLock by default, but if not: try `bindl` (fires even when locked/idle) or
check `misc:allow_session_lock_restore` settings.

### Fix if log shows key NOT seen at all (app consuming it):
On Hyprland, `bindd` fires compositor-side before app receives input — apps cannot intercept it.
If the key is genuinely not seen, the issue is a full input grab by a Wayland client (e.g. a game,
VM, or Electron app in pointer-lock mode). Check:
```bash
hyprctl activewindow | grep -E "class|fullscreen|inhibitIdle"
```

## Notes
- The `bindd` vs `bind` distinction: `d` just adds a description, no functional difference for firing
- `bindl` = fires even on lockscreen; `binde` = repeats while held; `bindr` = fires on key release
- Hyprland keybinds are compositor-side and CANNOT be intercepted by normal Wayland apps
- A second bind on same key+mod combo would shadow the first — check with `hyprctl binds | grep F4`
