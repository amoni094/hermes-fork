# Waybar power-button dropdowns on Wayland/Hyprland

Use this when a user says the power button should open as a real dropdown from the bar button, not a freestanding popup.

## Durable lesson

On Wayland, a custom GTK popup window launched from a shell script is not the same thing as a bar-anchored dropdown. If it is created as a temporary/floating window without a parent surface, GTK/GDK may emit messages like:

- `Window ... is a temporary window without parent, application will not be able to position it on screen.`

That window may appear near the top-right, but it is still just a standalone popup, not a true dropdown attached to the Waybar module.

## Preferred fix path

For a Waybar `custom/*` power button that must behave like a real dropdown:

1. Prefer Waybar's built-in menu support on the custom module:
   - `menu: "on-click"`
   - `menu-file: ".../power-menu.ui"`
   - `menu-actions: [ ... ]`
2. Define the menu in a GTK `.ui` file with a root `GtkMenu` object whose id is `menu`.
3. Put the actual power operations in a small wrapper script (`lock`, `suspend`, `logout`, `reboot`, `shutdown`) and map the menu items to those commands via `menu-actions`.
4. Reload Waybar after editing the module config.

## Why this is better

- The menu is owned by Waybar, so it opens from the actual bar button.
- It behaves like a proper dropdown/popover instead of a manually-positioned popup.
- It avoids chasing focus/position hacks in `rofi` or custom GTK launcher scripts.

## Verification

- Validate the `.ui` file parses as XML.
- Validate wrapper scripts with `bash -n`.
- Reload Waybar and confirm the process stays up.
- Click the bar button and confirm the menu opens from the module itself.

## Pitfall

If the user's requirement is specifically "a dropdown from the button", do not stop after making a top-right popup window. A visually similar popup is still the wrong class of solution.