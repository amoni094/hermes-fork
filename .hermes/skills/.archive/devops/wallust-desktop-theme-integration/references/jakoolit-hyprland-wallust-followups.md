# JakooLit/Hyprland wallust follow-ups

Use this as a compact reference when a wallust migration looks successful on disk but parts of the desktop still do not reflect it.

## Active-consumer audit order
1. Waybar: read the live `~/.config/waybar/style.css` and confirm it imports `../waybar/wallust/colors-waybar.css` rather than an older Catppuccin/static file.
2. Rofi: read `~/.config/rofi/config.rasi` and confirm the active `@theme` points to a theme that imports `~/.config/rofi/wallust/colors-rofi.rasi`.
3. Hyprland: confirm the live included config has `source = ~/.config/hypr/wallust/wallust-hyprland.conf`.
4. SwayNC: import `wallust/colors-wallust.css` directly in `~/.config/swaync/style.css`; do not rely on Waybar's generated CSS as a shared source of truth.
5. Wallpaper helper: after `wallust run`, explicitly reload Hyprland, SwayNC, and Waybar.

## Waybar compatibility trick
If the active Waybar CSS is still built around Catppuccin semantic names (`@mauve`, `@peach`, `@surface0`, `@overlay1`, etc.), do not rewrite the whole stylesheet first.

Instead, extend the wallust template to export those alias names. Keep:
- wallpaper-driven base/background/text values
- compatibility aliases for Catppuccin-style selectors

If the wallpaper is monochrome and all wallust-derived semantic aliases collapse into similar greys, pin only the accent aliases (`blue`, `green`, `yellow`, `red`, `mauve`, etc.) to readable stable hues while leaving the structural/base colors wallust-driven. This preserves contrast without discarding the wallpaper-driven background.

## Rofi verification
`rofi -dump-theme -config ~/.config/rofi/config.rasi` is a quick confidence check that the active theme resolves cleanly after changing `@theme` or imported wallust files.

## GTK alignment
If GTK theme state is only visible through `gsettings` and there are no local files yet, write explicit user config files so file-based theming matches the live desktop state:
- `~/.config/gtk-3.0/settings.ini`
- `~/.config/gtk-4.0/settings.ini`

Good stock fallback on Fedora Atomic when upstream theme assets are missing:
- `gtk-theme-name=Adwaita`
- `gtk-application-prefer-dark-theme=1`
- `gtk-icon-theme-name=Adwaita`
- `gtk-cursor-theme-name=default`

## Cava troubleshooting split
Separate two questions:
1. Did wallust successfully write a valid full Cava config file?
2. Does the Cava binary actually run with default and custom configs?

If wallust writes the config successfully but both `cava` and `cava -p ~/.config/cava/config` fail the same way, treat it as a runtime troubleshooting path separate from the wallust integration path.