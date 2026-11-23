# Rofi-backed power menu: focus, click-away dismissal, and small offset tuning

Use when a Waybar `custom/power` module opens an external launcher instead of a built-in Waybar `GtkMenu`.

## Recognition pattern
- `custom/power` uses `on-click` with a script such as `PowerMenu.sh`
- A `power-menu.ui` file may still exist in the config tree, but it is inactive unless the module is wired with `menu-file`
- Styling and placement live in a rofi `.rasi` theme and launcher flags

## Practical rules
- Inspect the script first; do not tune `GtkMenu` margins until you confirm the module actually uses Waybar's built-in popup.
- For small vertical placement changes, edit rofi theme `y-offset` in small increments.
- For toolbar-adjacent placement, keep `location` and `anchor` consistent with the bar edge and change offsets minimally.
- If the menu should dismiss when the user clicks away, avoid launcher flags that force standalone window behavior or unusual focus capture.

## Verified example from session
Script change:
- removed `-normal-window`
- removed `-steal-focus`

Theme change:
- `y-offset: 18` -> `y-offset: 8`
- text and selected-text aligned to wallust/toolbar foreground variables
- border/background aligned to shared theme variables instead of hard-coded colors

## Why this matters
A config directory can contain both:
- legacy Waybar built-in popup assets (`power-menu.ui`)
- current external launcher assets (`PowerMenu.sh`, rofi theme)

Touching the wrong layer wastes time and can create false confidence because the visible menu is controlled elsewhere.
