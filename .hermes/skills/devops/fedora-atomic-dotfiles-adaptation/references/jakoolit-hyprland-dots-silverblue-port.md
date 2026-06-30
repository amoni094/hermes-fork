# JaKooLit/Hyprland-Dots on Fedora Silverblue: practical port pattern

Use this as a concrete example when the user wants to borrow from JaKooLit or similar Hyprland repos without trusting the installer flow.

## Repo observations that matter
- The repo is fundamentally a user-config source built around `~/.config`.
- `config/hypr/hyprland.conf` is modular and sources `configs/` plus `UserConfigs/`.
- `copy.sh` is interactive and tries to manage backups, symlinks, and wallust initialization.
- Fedora support exists, but the installer assumptions are aimed at mutable Fedora workflows, not specifically Silverblue.
- The upstream README now points future maintenance to `LinuxBeginnings/Hyprland-Dots`.

## Safe components to copy
These were good candidates for a Silverblue-safe user-space port:
- `config/wezterm`
- `config/fastfetch`
- `config/btop`
- `config/cava`
- `config/hypr`
- `config/waybar`
- `config/rofi`
- `config/swaync`
- `config/wlogout`
- `config/wallust`
- `wallpapers/`

## Silverblue-safe patches that helped
1. Disable `initial-boot.sh` in `hyprland.conf` until dependencies are confirmed.
2. Change author defaults in `UserConfigs/01-UserDefaults.conf` to local tools.
   - Example from this session: `ptyxis` instead of `kitty`, `nautilus` instead of `thunar`.
3. Patch `configs/Startup_Apps.conf` so startup commands are guarded with `command -v ... >/dev/null && ...`.
4. Point `$wallDIR` at a copied user wallpaper path such as `~/Pictures/wallpapers/jakoolit`.
5. Comment out Quickshell / AGS startup by default unless the user asked for them.
6. Trim `wallust.toml` to the copied components and ensure target directories exist.

## Waybar-specific lesson
Manual copy can fail if `~/.config/waybar/config` or `style.css` are dangling symlinks.

Reliable recovery:
- remove the broken symlinks first
- copy a specific preset into concrete files, e.g.
  - `configs/[TOP] Default` -> `~/.config/waybar/config`
  - `style/[Catppuccin] Mocha.css` -> `~/.config/waybar/style.css`
- verify there are zero dangling symlinks afterward

## Recommended verification artifacts
After the copy, verify at least:
- `~/.config/hypr/hyprland.conf`
- `~/.config/hypr/configs/Startup_Apps.conf`
- `~/.config/hypr/UserConfigs/01-UserDefaults.conf`
- `~/.config/hypr/monitors.conf`
- `~/.config/waybar/config`
- `~/.config/waybar/style.css`
- `~/.config/rofi/config.rasi`
- `~/.config/swaync/config.json`
- `~/.config/hypr/hyprlock.conf`
- `~/.config/wallust/wallust.toml`

Also verify:
- wallpaper count at the chosen target path
- zero dangling symlinks in `~/.config/waybar`

## Why this generalizes
The durable lesson is not "JaKooLit works on Silverblue." The durable lesson is:
- use third-party ricing repos as config sources
- back up first
- copy selectively
- patch startup commands to tolerate missing binaries
- replace author defaults with local-safe ones
- verify by readback, not by assumption
