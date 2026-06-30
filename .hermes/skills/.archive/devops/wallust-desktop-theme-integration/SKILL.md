---
name: wallust-desktop-theme-integration
description: Integrate wallust into multi-app Linux desktop ricing stacks safely, especially Hyprland/Waybar/Rofi/SwayNC/Cava setups on Fedora Atomic/Silverblue.
---

# Wallust desktop theme integration

Reference support:
- `references/waybar-vitals-and-battery.md` — proven Waybar pattern for putting vitals to the left of the top-right status area, adding laptop battery support, and preferring shorthand text labels like `CPU`, `Mem`, `Temp`, `Disk`, and `Pwr` when icon-only vitals hurt readability.

Use this when:
- A Linux desktop ricing stack uses wallust or should be switched to wallust-driven colors.
- The stack includes Hyprland, Waybar, Rofi, SwayNC, Cava, or wallpaper-switch scripts.
- The host is Fedora Atomic/Silverblue and you want user-space, reversible changes.

## Goals
- Make wallust generation actually drive the active UI, not just produce unused files.
- Keep changes local to the user config when possible.
- Verify both generation and application.

## Preferred approach
1. Prefer user-space installation on Atomic/Silverblue when no trustworthy native package is present.
   - Good default: install the upstream release binary under `~/.local/opt/<tool>/<version>/` and symlink into `~/.local/bin/`.
   - Avoid layering unknown RPMs just to theme the desktop.
2. Audit the active config path for each app before editing templates.
   - Confirm the active Waybar stylesheet, active Rofi theme, Hyprland `source =` lines, SwayNC CSS imports, and wallpaper switch scripts.
3. Ensure wallust templates exist locally under `~/.config/wallust/templates/` for every target app.
4. Regenerate colors with a real wallpaper and verify that target files were rewritten.
5. Reload the affected UI components after regeneration.

## Integration checklist

### 1) Install and verify wallust
- Verify whether `wallust` is already available on PATH.
- If not present and no safe distro package is available, install locally under `~/.local/opt/...` and expose via `~/.local/bin/wallust`.
- Verify with `wallust --version`.

### 2) Make templates real
Typical targets:
- Hyprland: `~/.config/hypr/wallust/wallust-hyprland.conf`
- Waybar: `~/.config/waybar/wallust/colors-waybar.css`
- Rofi: `~/.config/rofi/wallust/colors-rofi.rasi`
- SwayNC: `~/.config/swaync/wallust/colors-wallust.css`
- Cava: `~/.config/cava/config`

If the wallust config references template files that do not exist, create them locally in `~/.config/wallust/templates/` and update `wallust.toml` to point to those files explicitly.

### 3) Audit active consumers
Do not assume generated files are used. Check the active consumer for each app:
- Waybar: the active stylesheet must import the wallust CSS, not an older theme pack.
- Rofi: the active theme in `config.rasi` must point to a theme that imports wallust colors.
- Hyprland: some active config file must `source = ~/.config/hypr/wallust/wallust-hyprland.conf`.
- SwayNC: import its own generated wallust CSS directly rather than piggybacking on another app's CSS.
- Cava: if wallust writes `~/.config/cava/config`, use a full-file template derived from the real config rather than a partial color snippet.

### 4) Add reloads to wallpaper-refresh flow
If a wallpaper switch script runs wallust, make sure it also refreshes consumers afterward. Good defaults:
- `hyprctl reload`
- `swaync-client --reload-config`
- `waybar-msg cmd reload` or `SIGUSR2` for Waybar

This is important because successful wallust generation alone does not guarantee the running desktop re-reads the files.

## Important pitfalls
- Generated != applied. A common failure mode is that wallust writes files successfully while the app still imports Catppuccin or some older static theme.
- For Waybar, keep compatibility aliases if the existing stylesheet expects Catppuccin-style names such as `@mauve`, `@peach`, `@surface0`, or `@overlay1`. Map them in the wallust template instead of rewriting the entire stylesheet immediately.
- If the wallpaper is monochrome and those semantic aliases become indistinguishable greys, keep wallust-driven base/background/text values but pin only the accent aliases (`blue`, `green`, `yellow`, `red`, `mauve`, etc.) to readable stable hues. This preserves contrast without losing wallpaper-driven structure.
- For SwayNC, import `wallust/colors-wallust.css` directly rather than importing Waybar's wallust CSS. This keeps notification theming independent and easier to debug.
- For Rofi, switching the active `@theme` may be the real fix; generating `colors-rofi.rasi` is not enough if `config.rasi` still points elsewhere. Validate with `rofi -dump-theme` after the change.
- For Cava, do not point wallust at `~/.config/cava/config` unless the template is a full config file. A partial template will overwrite and break the live config.
- When wallust owns the live Cava config, make the `[output] method` explicit in the generated file (for example `method = ncurses`). Do not rely on the implicit default path if runtime verification shows crashes; reduce to a minimal config first to distinguish theme-generation mistakes from Cava runtime/backend problems.
- For terminal emulators, prefer a two-layer setup: keep the main `kitty.conf` / Ghostty config tiny and stable, and have wallust generate only the app-specific color include under a `wallust/` subdirectory. This makes regeneration safe and preserves manual non-color settings.
- Monochrome wallpapers naturally yield grayscale-heavy palettes. Treat that as expected palette behavior, not as a template bug.

- Monochrome wallpapers naturally yield grayscale-heavy palettes. Treat that as expected palette behavior, not as a template bug.
- If GTK is only configured implicitly via `gsettings`, write explicit `~/.config/gtk-3.0/settings.ini` and `~/.config/gtk-4.0/settings.ini` so file-based theme state matches the live desktop.

## Verification sequence
1. Run wallust against a real wallpaper.
2. Confirm each target file exists and has a fresh mtime.
3. Reload Waybar, Hyprland, and SwayNC.
4. Validate Rofi by dumping the resolved theme.
5. Check relevant logs for parser/config errors.
6. If Cava is configured, verify both that wallust wrote the config and that Cava starts cleanly; distinguish integration success from a separate Cava runtime crash.
7. If Fedora-packaged Cava still crashes, test whether a newer user-space upstream build plus an explicit output method resolves it before treating Cava as incompatible with the rice.

## Session reference
- See `references/jakoolit-hyprland-wallust-stack.md` for a concrete Hyprland/Waybar/Rofi/SwayNC/Cava example and the specific integration pattern that worked.
- See `references/jakoolit-hyprland-wallust-followups.md` for the follow-up audit pattern: active-consumer checks, Waybar alias tuning for monochrome wallpapers, explicit GTK settings, and how to separate Cava runtime failures from wallust integration success.
- See `references/terminal-emulators-and-cava-followups.md` for the follow-up pattern that added wallust-generated Kitty/Ghostty configs and the explicit-Cava-output-method pitfall.
- See `references/cava-explicit-output-and-user-space-rebuild.md` for the Fedora-specific pattern where a wallust-generated Cava config needed an explicit `method = ncurses`, plus a Silverblue-safe user-space rebuild/shadowing path for newer Cava releases.
