# Kitty Numpad Arrow Key Fix (Wayland / Linux)

## Symptom
Pressing numpad arrow keys in kitty emits raw escape sequences instead of
working as history/cursor navigation:

    [1;129D  [1;129C  [1;129B  [1;129A

These are kitty's enhanced keyboard protocol sequences. `1;129` = modifier 129
= NumLock (128) + 1 (base). readline and most shells don't interpret them.

## Root cause
Kitty sends numpad keys as distinct key events (GLFW_FKEY_KP_UP etc.) with
the NumLock modifier (128) encoded in the CSI sequence. readline/bash expect
plain `\x1b[A` etc. without a modifier prefix.

## Fix — kitty.conf
Add to `~/.config/kitty/kitty.conf`:

```
# Numpad arrow keys — remap to plain arrow sequences (readline/history compatible)
map num_lock+kp_up    send_text all \x1b[A
map num_lock+kp_down  send_text all \x1b[B
map num_lock+kp_right send_text all \x1b[C
map num_lock+kp_left  send_text all \x1b[D
map kp_up             send_text all \x1b[A
map kp_down           send_text all \x1b[B
map kp_right          send_text all \x1b[C
map kp_left           send_text all \x1b[D
```

Reload without restarting: `kill -SIGUSR1 $(pgrep -x kitty)`

## Verification
Confirm the maps registered in kitty's keymap (correct key codes: 57417–57420,
NumLock modifier 128):

```python
kitty +runpy "
from kitty.config import load_config
import os, kitty.fast_data_types as fdt
cfg = os.path.expanduser('~/.config/kitty/kitty.conf')
c = load_config(cfg)
kp = {fdt.GLFW_FKEY_KP_UP, fdt.GLFW_FKEY_KP_DOWN, fdt.GLFW_FKEY_KP_LEFT, fdt.GLFW_FKEY_KP_RIGHT}
found = [(k,v) for k,v in c.keyboard_modes[''].keymap.items() if k.key in kp]
print('KP entries:', len(found))
for k,v in found: print(' mods=%d key=%d' % (k.mods, k.key), '->', v[0].definition)
"
```

Expected output: 8 entries (4 with mods=128, 4 with mods=0).

## Pitfalls
- `KP_Up` / `KP_Down` (uppercase with underscore) are NOT valid kitty map key names
  — they will be silently dropped. Use `kp_up` / `kp_down` (lowercase).
- `num_lock+up` (without the `kp_` prefix) also fails silently — must be `kp_up`.
- `len(c.map)` returns 0 (always empty); check `c.keyboard_modes[''].keymap` instead.
- `kitty --check-config` does not exist; use the `kitty +runpy` introspection above.
- `kill -SIGUSR1` reloads config live; no kitty restart required.

## Key code reference
| Key | GLFW code | kitty map name |
|-----|-----------|----------------|
| KP Up | 57419 | kp_up |
| KP Down | 57420 | kp_down |
| KP Left | 57417 | kp_left |
| KP Right | 57418 | kp_right |
| NumLock modifier | 128 | num_lock |
