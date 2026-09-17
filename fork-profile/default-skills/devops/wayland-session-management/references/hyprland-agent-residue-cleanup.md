# Hyprland agent-residue cleanup

Use this when a user migrated from one local agent/app to another and the old product still shows up in desktop/session wiring.

Checklist
1. Inspect `~/.config/autostart/*.desktop` for the retired product name.
2. Check generated user units with:
   - `systemctl --user list-unit-files | grep -i <old-name>`
   - `systemctl --user cat 'app-<name>@autostart.service'`
3. Read `SourcePath=` from the generated unit to find the real autostart `.desktop` file.
4. Audit helper scripts in `~/.local/bin` and user services in `~/.config/systemd/user` that still reference the retired product.
5. Stop and disable/remove the stale units and scripts.
6. If the residue carried a still-useful behavior (for example lock-on-lid), recreate it under a neutral or current-product name before finishing.
7. Reload the user manager and verify the current desktop session and the new agent still behave normally.

Verification
- `command -v <old-name>` returns nothing if the binary/package was also removed.
- `systemctl --user list-unit-files | grep -i <old-name>` returns nothing.
- `find ~/.config/autostart -maxdepth 1 -iname '*<old-name>*'` returns nothing.
- The current agent's gateway/dashboard services still report healthy after cleanup.
