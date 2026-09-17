# Firefox Link Opening on LXQt — Diagnosis and Fix

## Symptom
Clicking a hyperlink in any app (file manager, media player, another app) opens
a "Close Firefox" or "A copy of Firefox is already open" dialog instead of
opening the link as a new tab in the running browser.

## Root Cause: stale Default profile in profiles.ini

Firefox maintains two sets of profile selection:
- `installs.ini` / `[InstallXXX]` sections — the authoritative default for this
  Firefox binary installation
- `[Profile*]` sections — can also carry `Default=1`

When both exist and point to DIFFERENT profiles, a fresh Firefox invocation
(from xdg-open / a clicked link) uses the `[Profile*]` Default=1 profile while
the running instance holds a lock on the Install-section profile. The new
process cannot hand off to the existing window via single-instance IPC, so it
shows the lock-conflict dialog.

## Diagnosis

```bash
# Check which profiles exist and which carry Default=1
cat ~/.mozilla/firefox/profiles.ini

# Check what profile the running instance has locked
ls -la ~/.mozilla/firefox/*/.parentlock

# Check installs.ini (authoritative install default)
cat ~/.mozilla/firefox/installs.ini
```

Sign of the bug: `profiles.ini` has a `[Profile*]` stanza with `Default=1`
pointing to a DIFFERENT path than what `installs.ini` says.

## Fix

1. Remove `Default=1` from the stale `[Profile*]` entry:
   ```bash
   # Back up first
   cp ~/.mozilla/firefox/profiles.ini ~/.mozilla/firefox/profiles.ini.bak
   # Remove Default=1 from the old profile block only
   # Use a targeted sed that only affects the block containing the stale profile name
   sed -i '/^\[Profile1\]/,/^$/{/^Default=1/d}' ~/.mozilla/firefox/profiles.ini
   ```
   Adjust `Profile1` to match the stale profile's block header.

2. Add `--new-tab` guard to any Firefox wrapper script:
   ```bash
   # In /usr/local/bin/firefox or similar wrapper:
   # If Firefox is already running AND a URL is passed, route to existing window
   if [ $# -gt 0 ] && pgrep -u "${USER:-galina}" -x firefox >/dev/null 2>&1; then
       exec /usr/lib/firefox/firefox --new-tab "$@"
   fi
   exec /usr/lib/firefox/firefox "$@"
   ```
   This is belt-and-suspenders — the profiles.ini fix alone should restore IPC,
   but `--new-tab` prevents a second instance from opening even if the profile
   resolution is ambiguous.

3. Kill any stale "Close Firefox" dialog:
   ```bash
   # Find second (non-main) firefox processes
   MAIN=$(pgrep -u galina firefox | head -1)
   for pid in $(pgrep -u galina firefox); do
     [ "$pid" != "$MAIN" ] && kill $pid
   done
   # Close the dialog window
   DISPLAY=:0 XAUTHORITY=$(find /tmp -name 'xauth_*' -user galina | head -1) \
     wmctrl -c 'Close Firefox'
   ```

## Verification

```bash
# xdg-open should return immediately and NOT spawn a second firefox process
sudo -u galina DISPLAY=:0 \
  XAUTHORITY=$(find /tmp -name 'xauth_*' -user galina | head -1) \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  xdg-open 'https://example.com'
# After this returns: pgrep -u galina firefox should still show only 1 PID
```

## Pitfalls

- Do NOT remove the `[Install*]` Default entry — that is the authoritative one;
  only remove `Default=1` from the `[Profile*]` stanzas.
- `sed -i '/^\[Profile0\]/,/^$/{/^Default=1/d}'` operates per-block; confirm
  the right profile number before running (Profile0 vs Profile1 etc).
- The `--new-tab` flag only works if xdg-open inherits the correct DBUS_SESSION_BUS_ADDRESS;
  always pass it explicitly when calling from sudo or SSH.
