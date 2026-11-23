# Waybar network launcher fallbacks

Use this when a Hyprland/Waybar network module click action fails with a vague launcher error instead of opening a network tool.

## High-yield checks

1. Read the Waybar module definition first.
   - Look for `on-click`, `on-click-right`, or a wrapper script such as `WaybarScripts.sh --nmtui`.
2. Read the wrapper script instead of assuming the module calls `nmtui` directly.
3. Verify three things separately:
   - the configured terminal binary exists
   - the target helper exists (`nmtui`, `nm-connection-editor`)
   - the terminal supports the invocation form being used

## Common failure shape

A script contains:

```bash
elif [[ "$1" == "--nmtui" ]]; then
    $term nmtui
```

This has two distinct failure modes:
- `nmtui` is not installed
- the terminal does not accept `terminal cmd` syntax for child execution

On Fedora systems using Kitty, `kitty -e nmtui` is the safer form.

## Robust pattern

```bash
if command -v nmtui >/dev/null 2>&1; then
    case "$term" in
        kitty)
            kitty -e nmtui
            ;;
        *)
            $term -e nmtui
            ;;
    esac
elif command -v nm-connection-editor >/dev/null 2>&1; then
    nm-connection-editor &
else
    notify-send "Waybar: network" "Neither nmtui nor nm-connection-editor is installed."
fi
```

## Interpretation rule

If the fallback GUI opens and the session otherwise looks healthy, treat the original error as a helper-binary / launcher-script issue, not a compositor-session failure.
