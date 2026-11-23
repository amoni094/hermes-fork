# JaKooLit-style Hyprland stack with wallust

This reference captures a concrete working pattern for a Hyprland desktop where wallust colors were present but not consistently applied.

## Working target set
- Hyprland output: `~/.config/hypr/wallust/wallust-hyprland.conf`
- Waybar output: `~/.config/waybar/wallust/colors-waybar.css`
- Rofi output: `~/.config/rofi/wallust/colors-rofi.rasi`
- SwayNC output: `~/.config/swaync/wallust/colors-wallust.css`
- Cava output: `~/.config/cava/config`

## Effective fixes

### Waybar
Problem:
- Active stylesheet still imported Catppuccin, so wallust generation had no visible effect.

Fix:
- Point the active Waybar stylesheet at `../waybar/wallust/colors-waybar.css`.
- Preserve compatibility by defining Catppuccin-style aliases in the wallust template, including names such as:
  - `@overlay1`
  - `@surface0`
  - `@mauve`
  - `@peach`
  - `@theme_base_color`
  - `@theme_text_color`

Why this matters:
- It lets an existing themed stylesheet keep working while the palette source changes to wallust.

### Rofi
Problem:
- `colors-rofi.rasi` was generated, but the active `config.rasi` still selected another theme file.

Fix:
- Switch `config.rasi` to a theme that actually imports `~/.config/rofi/wallust/colors-rofi.rasi`.
- Validation method: `rofi -dump-theme -config ~/.config/rofi/config.rasi`.

### Hyprland
Pattern that worked:
- Ensure an active Hyprland config file contains:
  - `source = $HOME/.config/hypr/wallust/wallust-hyprland.conf`
- After wallust regeneration, run `hyprctl reload`.

### SwayNC
Problem:
- SwayNC was importing Waybar's wallust CSS instead of its own generated file.

Fix:
- Import `wallust/colors-wallust.css` directly from `style.css`.
- Reload with `swaync-client --reload-config` and check user journal for config/parser issues.

### Cava
Safer integration pattern:
- If wallust targets `~/.config/cava/config`, use a full config template derived from the real config, not a partial snippet.
- Parameterize background/foreground/gradient colors only.
- After generation, treat `wallust wrote the config` and `cava starts cleanly` as separate checks.

## Wallpaper refresh script pattern
A working refresh tail looked like:
1. run wallust
2. reload Hyprland
3. reload SwayNC config
4. reload Waybar via `waybar-msg cmd reload` or `SIGUSR2`

Reason:
- Generation alone did not guarantee the running apps re-read the changed files.

## Verification signals
- `wallust run -s <wallpaper>` writes all configured targets.
- mtimes of target files advance after a wallpaper refresh script run.
- `rofi -dump-theme` exits 0.
- `hyprctl reload` returns `ok`.
- SwayNC journal shows config reload without fresh parser errors.

## Caution on palette expectations
- A monochrome wallpaper yielded a grayscale-heavy palette.
- This was expected output from the image and should not be mistaken for a broken template.
