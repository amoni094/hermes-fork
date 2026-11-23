# Terminal emulators and Cava follow-ups

Concrete follow-up pattern from a Fedora Silverblue Hyprland wallust stack.

## Cava: full-file template and explicit output method

If wallust writes `~/.config/cava/config`, treat the template as the full live Cava config, not a partial color include.

Important observed pitfall:
- Leaving `[output] method` implicit in the generated config caused reproducible crashes on the tested setup.
- Regenerating the same config with an explicit line:
  - `method = ncurses`
  stabilized runtime verification.

Recommended verification split:
1. Verify wallust generation wrote `~/.config/cava/config`.
2. Verify Cava starts with the generated config.
3. If Cava fails, reduce to a minimal config to separate theme-generation problems from runtime/backend problems.
4. If a local rebuild is needed on Atomic/Silverblue, prefer a user-space binary under `~/.local/opt/<tool>/<version>/` and expose it through `~/.local/bin/` rather than layering system packages.

## Kitty / Ghostty: generated-colors plus tiny stable entrypoint

Prefer a two-layer structure:
- wallust writes app-specific generated colors into a dedicated `wallust/` subdirectory
- the main app config stays tiny and stable, only importing the generated file plus a few non-color settings

Example pattern:
- Kitty main config includes `~/.config/kitty/wallust/colors-kitty.conf`
- Ghostty main config points to `~/.config/ghostty/wallust/colors-ghostty.conf`

This keeps regeneration safe and makes manual tweaks to non-color settings durable.

## Monochrome wallpaper handling

When the wallpaper is grayscale-heavy, keep wallpaper-driven background/text values but pin semantic accents to readable hues across apps.

Useful stable cross-app accent set:
- primary/selection: `#89b4fa`
- secondary/accent: `#cba6f7`
- info/alternate: `#74c7ec`
- success: `#a6e3a1`
- warning: `#f9e2af`
- urgent/error: `#ff6b6b`

Apply those pinned accents in templates for:
- Waybar alias colors
- Rofi selected/active/urgent states
- SwayNC border/urgent/success variables
- terminal palettes when readability matters more than pure extraction fidelity
