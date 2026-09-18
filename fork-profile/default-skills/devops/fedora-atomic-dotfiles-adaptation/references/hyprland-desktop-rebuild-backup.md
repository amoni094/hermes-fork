# Hyprland desktop rebuild backup pattern on Fedora Atomic

Use this before risky Hyprland/Waybar/Rofi/SwayNC theming changes, or immediately after a known-good state, so the desktop can be rebuilt from user-space assets instead of memory.

## Goal
Capture more than `~/.config/hypr` alone. A rebuild snapshot should include adjacent desktop configs, wallpapers, and package-state manifests.

## Recommended contents
- `~/.config/hypr`
- `~/.config/waybar`
- `~/.config/rofi`
- `~/.config/swaync`
- `~/.config/wallust`
- terminal/app configs that the theme depends on when present:
  - `~/.config/kitty`
  - `~/.config/fastfetch`
  - `~/.config/btop`
  - `~/.config/cava`
- wallpapers/assets used by the setup, e.g. `~/Pictures/wallpapers/<theme>`

Also capture rebuild context:
- `rpm-ostree status`
- `rpm-ostree status --json`
- Flatpak app list
- Flatpak runtime list
- a sorted file manifest
- a restore helper script

## Layout
Store under a timestamped backup root such as:
- `~/backups/hyprland/desktop-rebuild-YYYYmmdd-HHMMSS/`
- `~/backups/hyprland/desktop-rebuild-YYYYmmdd-HHMMSS.tar.gz`
- `~/backups/hyprland/desktop-rebuild-YYYYmmdd-HHMMSS.manifest.txt`
- `~/backups/hyprland/restore-desktop-rebuild-YYYYmmdd-HHMMSS.sh`

## Restore-script requirements
The restore helper should:
1. make a pre-restore safety backup of the current target directories
2. replace only the captured user-space directories
3. leave a clear path to the safety backup in stdout

## Why this matters on Fedora Atomic
On Silverblue/Kinoite-style systems, app/runtime availability may depend on a staged `rpm-ostree` deployment rather than the current boot. Capturing `rpm-ostree` and Flatpak state beside the configs makes later rebuilds much faster and reduces guesswork about which packages the theme expected.

## Reporting checklist
When you create the backup, report:
- archive path
- snapshot directory
- restore script path
- SHA256
- size in bytes
- file count
- which config trees and wallpaper/assets were included

## Pitfall
A `~/.config/hypr`-only archive is often not enough for a practical rebuild. Without Waybar/Rofi/SwayNC/Wallust and wallpaper assets, the restored session may boot but still lose most of the intended desktop behavior and theming.
