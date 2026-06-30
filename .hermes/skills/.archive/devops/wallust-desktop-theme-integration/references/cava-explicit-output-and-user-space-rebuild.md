# Cava explicit output + user-space rebuild pattern

Use this reference when wallust writes a full `~/.config/cava/config` and Cava appears to crash afterward on Fedora Atomic/Silverblue.

## Symptom pattern
- `wallust run -s <wallpaper>` succeeds.
- The generated Cava config looks visually reasonable.
- `cava -p ~/.config/cava/config` segfaults or exits 139.
- Minimal raw output tests may still work.

## Debugging sequence
1. Do not assume the colors caused the crash.
2. Test a minimal config for each output path you care about:
   - `method = raw`
   - `method = noncurses`
   - `method = ncurses`
3. If minimal terminal-output configs work but the wallust-generated full config crashes, inspect whether the generated file left the output method commented out.
4. Regenerate with an explicit output choice in the wallust template, usually:
   - `[output]`
   - `method = ncurses`
5. Re-run wallust and verify the generated config now contains an active output method line.
6. Re-test `cava -p ~/.config/cava/config` with timeout-based verification.

## Durable fix
In the wallust Cava template, emit an explicit output mode instead of relying on Cava defaults. Example:

```ini
[output]
method = ncurses
```

This avoids a failure mode where the implicit/default output path behaves differently from the known-good explicit one.

## If the distro build is still suspect
On Fedora Atomic/Silverblue, a narrow recovery path is:
1. Build a newer upstream Cava release in a Fedora container (`podman run fedora:<release> ...`).
2. Install the resulting binary into a versioned user path such as `~/.local/opt/cava/<version>/cava`.
3. Shadow the system binary via `~/.local/bin/cava`.
4. Keep the wallust template fix in place so future regenerations remain stable.

## Reporting rule
When this works, report both pieces separately:
- wallust integration fix: explicit output mode in the generated config
- runtime fix: user-space Cava binary override, if one was needed

Do not collapse them into a vague "Cava was broken" conclusion.