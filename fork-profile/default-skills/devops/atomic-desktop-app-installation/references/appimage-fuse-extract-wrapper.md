# AppImage FUSE extract + wrapper pattern on Atomic desktops

Use when an upstream Linux desktop app ships primarily as an AppImage and the direct launch fails because `libfuse.so.2` is absent or undesirable to add immediately.

## Durable pattern
1. Download AppImage into `~/Applications/`.
2. `chmod +x` it.
3. Try a direct `--version` or short launch first.
4. If FUSE is missing, run `--appimage-extract`.
5. Use the extracted `squashfs-root/` as the payload.
6. Create a wrapper under `~/.local/bin/<app>` that:
   - exports `APPDIR` to the extracted root
   - executes `"$APPDIR/AppRun"`
   - carries any needed runtime flags
7. Create a local `.desktop` entry pointing at the wrapper.
8. Verify the process stays alive briefly after launch.

## Why `APPDIR` matters
Some extracted AppImages do not resolve `AppRun` correctly when launched outside the embedded AppImage runtime. If the log shows `No such file or directory` for a payload path that should be inside the extracted tree, export `APPDIR` explicitly in the wrapper before invoking `AppRun`.

Minimal wrapper shape:

```bash
#!/usr/bin/env bash
set -euo pipefail
export APPDIR="$HOME/Applications/squashfs-root"
exec "$APPDIR/AppRun" "$@"
```

## When to add Electron/Chromium flags
Only after observing the real error stream.

Useful examples from this session class:
- `--no-sandbox` for sandbox constraints
- `--ozone-platform=x11` when Wayland/Vulkan path is unstable
- `--disable-vulkan` when the log explicitly reports Vulkan incompatibility
- software-rendering fallback only if GPU initialization remains unstable after the narrower flags

## Verification shape
A strong lightweight check is:
- start the wrapper in background
- sleep ~5 seconds
- confirm the process is still alive
- then terminate it cleanly
- read back the first lines of the log to distinguish warnings from fatal errors

## Session note: Orca on Fedora Atomic
A working install shape for the Orca AppImage on this Fedora Atomic host used:
- payload: `~/Applications/orca-linux.AppImage`
- extracted runtime: `~/Applications/squashfs-root/`
- wrapper: `~/.local/bin/orca`
- desktop entry: `~/.local/share/applications/orca.desktop`
- wrapper flags: `--no-sandbox --ozone-platform=x11 --disable-vulkan --use-gl=swiftshader`

Observed behavior:
- direct AppImage launch failed on missing FUSE
- extracted `AppRun` initially mis-resolved `/orca-ide` until `APPDIR` was exported
- app then stayed running during a 5-second launch check, despite non-fatal GL/GPU warnings in the log

## Scope boundary
Do not turn this into a rule that all AppImages need extraction or software rendering. The durable lesson is the fallback sequence:
- try direct launch
- extract if FUSE/runtime support is the blocker
- wrap with `APPDIR` if extracted `AppRun` path resolution is wrong
- add only the minimum runtime flags justified by observed logs
