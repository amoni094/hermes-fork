# Chrome Bookmark Migration via Google Takeout

**Session date:** 2026-09-02  
**Context:** Chromium snap removed from Galina's laptop; bookmarks on old OS since uninstalled.

## Key finding: snap remove wipes all profile data

`snap remove chromium` deletes `~/snap/chromium/` entirely, unlike `.deb` uninstall
which leaves `~/.config/chromium/`. After snap removal there is NO local recovery path.

Contrast:
- `sudo apt remove chromium-browser` (deb) → leaves `~/.config/chromium/` intact
- `sudo snap remove chromium` → deletes `~/snap/chromium/` completely
- `sudo snap remove --purge chromium` → same result (purge is the default)

Snap may create a snapshot before removal (Ubuntu 20.04+). Check:
```bash
sudo snap saved  # lists snapshots
sudo snap restore <snapshot-id>  # restores if exists
```

## Recovery path: Google Takeout (Chrome Sync)

If the user was signed into Google in Chromium, bookmarks sync to Google's servers.
Recover via Google Takeout from any signed-in browser (including Firefox).

### Pre-filtered Takeout URL

```
https://takeout.google.com/takeout/custom/chrome
```

This URL opens Takeout pre-filtered to Chrome only: "1 of 1 selected" — no need to
manually deselect dozens of other Google products first.

Note: `https://www.google.com/bookmarks/?output=export` is the OLD Google Bookmarks
service (not Chrome Sync) and is NOT the right URL.

### Step-by-step (verified 2026-09-02)

1. Open `https://takeout.google.com/takeout/custom/chrome` in the signed-in Firefox
2. Verify: "1 of 1 selected", Chrome checkbox checked, "All Chrome data included"
3. Click "Next step" (blue button, bottom-right of the Step 1 panel)
4. Step 2: default settings are correct — "Send download link via email", "Export once"
5. Scroll down to find "Create export" button
6. Click "Create export"
7. Confirmation: "Google is creating a copy of data from Chrome" — email arrives in minutes to hours

### Import: PREFERRED method — direct SQLite write

The Firefox Library UI (Import and Backup dialog) is unreliable to drive remotely
via xdotool — the Library window is a separate floating window whose position shifts,
and toolbar button clicks require precise coordinates. The direct SQLite approach is
faster, more reliable, and verified working.

**Precondition: Firefox must be closed before writing to places.sqlite.**

```bash
# 1. Close Firefox cleanly
sudo -u galina DISPLAY=:0 xdotool key ctrl+q
sleep 3
# If still running:
sudo kill -TERM $(pgrep firefox)
sleep 3
pgrep firefox && echo 'still running' || echo 'closed'

# 2. Extract the Takeout zip
sudo -u galina unzip -o ~/Downloads/takeout-*.zip -d ~/Downloads/takeout/
# Bookmarks.html is at: ~/Downloads/takeout/Takeout/Chrome/Bookmarks.html

# 3. Copy the import script to the machine and run it:
#    (see templates/import-chrome-bookmarks.py)
sudo python3 /tmp/import_bookmarks.py

# 4. Restart Firefox
sudo -u galina DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus firefox &>/dev/null &
```

The script creates a folder "Imported from Chrome" under Other Bookmarks and inserts
all HTTP/HTTPS/FTP bookmarks from the HTML file. It backs up places.sqlite first
(`places.sqlite.bak_YYYYMMDD_HHMMSS`) and is idempotent — running it twice creates
two folders (each import is a separate folder), which is fine.

Verification after restart (DB is locked while Firefox runs — verify via Library UI):
- Firefox: Ctrl+Shift+O → Library window → Other Bookmarks → "Imported from Chrome"
- Or wait until Firefox is closed again and run:
  ```bash
  sudo python3 -c "
  import sqlite3
  conn = sqlite3.connect('/home/galina/.mozilla/firefox/cedyyfvu.default-release/places.sqlite')
  c = conn.cursor()
  c.execute(\"SELECT COUNT(*) FROM moz_bookmarks mb JOIN moz_bookmarks f ON mb.parent=f.id WHERE f.title='Imported from Chrome'\")
  print('Bookmarks imported:', c.fetchone()[0])
  conn.close()
  "
  ```

### Import: FALLBACK method — Firefox Library UI

Use this if Firefox cannot be closed (active user session, running media, etc.).

1. In Firefox: Bookmarks menu → Manage Bookmarks (Ctrl+Shift+O)
2. In the Library window toolbar: click "Import and Backup"
3. Click "Import Bookmarks from HTML..."
4. Navigate to: `~/Downloads/takeout/Takeout/Chrome/Bookmarks.html`
5. Click Open
6. Bookmarks appear under "Imported from Chrome" in Other Bookmarks

Pitfall: if driving this remotely via xdotool, the Library window's position varies
and its toolbar buttons are hard to target precisely. Use `scrot -u` to capture
the Library window specifically, not the full screen.

## xdotool remote GUI driving: dual-monitor coordinate notes

Galina's machine: 1366x768 laptop + 1920x1080 TV extended = 3286x1080 virtual desktop.
Firefox window geometry: `1366x715+0+21` (size + offset).

### Pitfall: scrot vs scrot -u

`scrot /tmp/screen.png` captures full 3286x1080 virtual desktop.
Vision model estimates are then wildly off relative to Firefox bounds.

`scrot -u /tmp/win.png` captures only the active window (1366x715).
Coordinates from vision model are now correct relative to the window image.
Add y_offset=21 (window top-left on screen) for absolute click coordinates.

### Coordinate arithmetic (example from session)

- `scrot -u` image size: 1366x715
- Vision model (on cropped region=[0,380,1000,715]) says button at (918, 86)
- Crop y-offset: 380. Absolute in window image: (918, 380+86=466)
- Window y-offset on screen: +21. Final screen coords: (918, 466+21=487)
- Click: `xdotool mousemove 918 487 click 1`

### Takeout Step 1 → Step 2 "Next step" button

In Firefox window (1366x715), the "Next step" button in Takeout Step 1:
- Approximately x=821–932, y=429–466 depending on scroll state
- Always scroll to bottom (xdotool key End) before attempting to click

### Takeout Step 2 "Create export" button

After scrolling to bottom in Step 2:
- Approximately x=918, y=531 in screen coordinates (window y_offset=21)
