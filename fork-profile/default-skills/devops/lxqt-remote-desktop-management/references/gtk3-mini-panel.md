# GTK3 Mini-Panel for Galina (launch-button.py)

Deploy to `/usr/local/bin/launch-button.py` (chmod +x).  
Entry point: `/usr/local/bin/galina-panel-start.sh` called from `/etc/xdg/autostart/lxqt-panel.desktop` via `/usr/local/bin/lxqt-panel-wrapped`.

## Architecture

Three cooperating processes:

```
[launch-button.py] — GTK3, DOCK window, full width
  ├── [▶ Apps] → rofi -show drun -show-icons
  ├── [spacer] — tint2 sits above this zone
  ├── [tray_box] — pack_end, grows left from clock; SNI icons land here
  ├── [battery label] — pack_end, reads /sys/class/power_supply/BAT0 directly
  ├── [clock]   — pack_end
  └── [⏻]      — pack_end → GTK leave dialog (Gtk.WindowPosition.CENTER_ALWAYS)

[tint2] — GTK2 taskbar, no systray, centered

[nm-applet / pasystray] — SNI tray apps; register with launch-button's watcher
```

## CRITICAL: ayatana-indicator-application-service steals the watcher name

`ayatana-indicator-application-service` starts early in the LXQt session and
claims `org.kde.StatusNotifierWatcher` on the session bus (low bus ID e.g. `:1.63`).
All tray apps (nm-applet, pasystray) call `RegisterStatusNotifierItem` on IT, not
on launch-button.py's watcher — even though our watcher registers with
`replace_existing=True`, it only wins when it starts BEFORE ayatana.

**Symptom:** `_registered_keys` stays empty; all 3 tray apps running; DBus property
`RegisteredStatusNotifierItems` returns items (served by ayatana's watcher object,
not ours); our `_add_icon` is never called.

**Diagnose:**
```bash
# Check who actually owns the watcher name:
sudo -u galina DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  dbus-send --session --print-reply \
  --dest=org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus.GetNameOwner \
  string:'org.kde.StatusNotifierWatcher' 2>&1
# Should be our panel's bus ID — if it's a low ID (e.g. :1.63), ayatana owns it

# Find the owning process:
sudo -u galina DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  dbus-send --session --print-reply \
  --dest=org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus.GetConnectionUnixProcessID string:':1.63'
ps -p <PID> -o pid,cmd
# If it shows ayatana-indicator-application-service, that's the culprit
```

**Fix — permanent (survives reboots):**
```bash
# 1. XDG autostart override
sudo tee /home/galina/.config/autostart/ayatana-indicator-application.desktop > /dev/null << 'EOF'
[Desktop Entry]
Hidden=true
EOF
sudo chown galina:galina /home/galina/.config/autostart/ayatana-indicator-application.desktop

# 2. Mask the systemd user service too (belt and suspenders)
sudo -u galina XDG_RUNTIME_DIR=/run/user/1000 systemctl --user mask \
  ayatana-indicator-application.service ayatana-indicators.target
```

**Fix — galina-panel-start.sh (kill it at panel startup):**
```bash
pkill -x ayatana-indicator-application-service 2>/dev/null
```
Add this to the kill block before launching launch-button.py.

## Critical: SNI watcher threading

`RegisterStatusNotifierItem` fires on a dbus-python worker thread. **Never create
or modify GTK widgets directly from that thread** — even `GLib.idle_add()` from
a DBus method handler may not dispatch if the DBusGMainLoop integration isn't
perfect. Use a **thread-safe queue** polled by a GLib timer on the GTK thread:

```python
import queue as Queue
_sni_queue = Queue.Queue()

# DBus method (runs on dbus thread) — also track in _registered_keys
@dbus.service.method(SNI_WATCHER_IFACE, in_signature='s', sender_keyword='sender_name')
def RegisterStatusNotifierItem(self, service, sender_name=None):
    key = f'{sender_name}{service}' if service.startswith('/') else service
    self._registered_keys.add(key)
    _sni_queue.put(('add', key))

# In main() — runs on GTK main thread every 250ms
def _process_queue():
    while not _sni_queue.empty():
        action, key = _sni_queue.get_nowait()
        if action == 'add':
            watcher._add_icon(key)
    return True  # keep running
GLib.timeout_add(250, _process_queue)
```

Why `GLib.idle_add` alone FAILS: the dbus-python worker thread's idle_add
call schedules into GLib's default context, but if there's any mainloop
integration gap the callback never fires. The queue + timer approach is
guaranteed to run on the GTK thread because the timer fires from `Gtk.main()`.

### Late pickup — use direct attribute read, NOT DBus self-query

Do NOT query `org.kde.StatusNotifierWatcher` via dbus-send or the session bus
from within the same process — this is a circular call that may deadlock or
silently return empty. Read `watcher._registered_keys` directly:

```python
_late_attempts = [0]
def _late_pickup():
    _late_attempts[0] += 1
    for key in list(watcher._registered_keys):
        if key not in watcher._items:
            watcher._add_icon(key)
    return _late_attempts[0] < 60   # poll for 30s (60 × 500ms)
GLib.timeout_add(500, _late_pickup)
```

Also: watcher needs `self._registered_keys = set()` in `__init__` and
`self._registered_keys.add(key)` in `RegisterStatusNotifierItem`.

## Critical: tray_box must use pack_end + pre-allocated size

The hbox layout is `[apps | spacer (expand=True) | ... ]`. Any widget placed
with `pack_start` into the spacer zone gets **zero allocated width** — the
expanding spacer consumes all remaining space. tray icons packed this way are
never rendered visible.

```python
# WRONG — tray_box ends up with 0px width under the expand spacer:
hbox.pack_start(tray_box, False, False, 4)

# CORRECT — pack_end places widgets right-to-left.
# CRITICAL: with pack_end, the LAST call ends up RIGHTMOST on screen.
# To put the power button in the far-right corner, pack it LAST:
tray_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
tray_box.set_size_request(90, 28)   # pre-allocate space; icons added dynamically
hbox.pack_end(tray_box, False, False, 4)   # leftmost of right cluster
hbox.pack_end(bat_lbl, False, False, 0)    # battery label next
hbox.pack_end(clock, False, False, 8)       # clock
hbox.pack_end(power_btn, False, False, 0)   # far right corner — pack LAST
```

Pitfall: if you pack power_btn before clock (common mistake), it ends up to
the LEFT of the clock. `pack_end` call order is the reverse of screen order.

**Pre-allocate tray_box with `set_size_request(90, 28)` at build time** rather
than growing it per icon. Dynamic `set_size_request` inside `_add_icon` on a
DOCK window that's already mapped doesn't reliably trigger relayout.

When adding icons dynamically to an already-mapped DOCK window:
- Call `btn.show_all()` then `self.tray_box.show_all()` then `self.win.queue_resize()`
- Use `queue_resize()`, NOT `queue_draw()` — DOCK windows don't repaint children
  on `queue_draw` if their allocated size is already locked
- Pre-allocating via `set_size_request` is more reliable than growing post-map

Also must call `btn.set_always_show_image(True)` on each tray button — GTK3
themes hide button images by default; without this the icon is invisible even
though the button widget exists.

## SNI icon visibility — use symbolic icons

Non-symbolic icons (e.g. `nm-signal-50`) may render as pale/faint on light
panel backgrounds. Symbolic icons always render in the foreground color (solid,
contrasting). Try symbolic first:

```python
theme = Gtk.IconTheme.get_default()
if icon_name:
    sym = icon_name + '-symbolic'
    if theme.has_icon(sym):
        img.set_from_icon_name(sym, Gtk.IconSize.LARGE_TOOLBAR)  # 24px
        placed = True
    elif theme.has_icon(icon_name):
        img.set_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        placed = True
```

Add a dark semi-transparent background to tray buttons so icons contrast on
light panels:
```css
.tray-btn {
    padding: 0 3px;
    min-width: 26px; min-height: 26px;
    background: rgba(0,0,0,0.12);
    border-radius: 3px;
}
.tray-btn image { opacity: 1; -gtk-icon-effect: none; color: #1a1a1a; }
```

## Battery: use native GTK label, not cbatticon

cbatticon uses **XEmbed**, not SNI — it will not appear in the SNI tray.
Embed battery info directly as a GTK label in the panel:

```python
def read_battery():
    import pathlib
    for bat in ['BAT0', 'BAT1']:
        p = pathlib.Path(f'/sys/class/power_supply/{bat}')
        if not p.exists(): continue
        try:
            cap = int((p / 'capacity').read_text().strip())
            status = (p / 'status').read_text().strip()
            return cap, status in ('Charging', 'Full')
        except Exception: pass
    return None

def update_battery(label):
    info = read_battery()
    if info is None:
        label.set_visible(False)
        return True
    pct, charging = info
    icon = '🪫' if pct < 20 else '🔋'
    label.set_text(f'{icon}{pct}%{("+" if charging else "")}')
    label.set_visible(True)
    return True

# In build_panel():
bat_lbl = Gtk.Label()
bat_lbl.get_style_context().add_class('battery-lbl')
update_battery(bat_lbl)
GLib.timeout_add_seconds(60, update_battery, bat_lbl)
hbox.pack_end(bat_lbl, False, False, 0)
```

## nm-tray: binary replacement when lxqt-session supervises it

If `lxqt-session` is the parent of `nm-tray` (check `/proc/<pid>/status | grep PPid`
then `ps -p <ppid>`), lxqt-session supervises and immediately respawns nm-tray
after every `pkill`. `Hidden=true` in `~/.config/autostart/nm-tray-autostart.desktop`
is ignored by lxqt-session's built-in module launcher.

**Fix: replace the nm-tray binary with a no-op stub:**
```bash
sudo mv /usr/bin/nm-tray /usr/bin/nm-tray.disabled
sudo tee /usr/bin/nm-tray > /dev/null << 'EOF'
#!/bin/bash
# Disabled — nm-applet handles network tray via SNI in galina-panel
exit 0
EOF
sudo chmod +x /usr/bin/nm-tray
```
lxqt-session will keep respawning it, but the stub exits immediately and leaves
no DBus registration or process alive.

Note: also ensure the autostart override filename matches exactly:
```bash
ls /etc/xdg/autostart/ | grep nm-tray   # find exact filename first
# Create override with matching name:
sudo tee /home/galina/.config/autostart/nm-tray-autostart.desktop > /dev/null << 'EOF'
[Desktop Entry]
Hidden=true
EOF
```

## Power/shutdown buttons: polkit fails for sudo-launched processes

If launch-button.py is started via `sudo -u galina`, polkit does not treat it
as the active console session (`subject.active = false`). `systemctl poweroff/reboot`
returns "Access denied" even with a polkit `.rules` file. Polkit rules files with
`subject.local && subject.active` will NOT work.

Fix: use sudoers NOPASSWD for the specific commands and call them with `sudo`:

```bash
# /etc/sudoers.d/galina-power  (chmod 440, visudo -c to validate)
galina ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff, /usr/bin/systemctl reboot, /usr/bin/systemctl suspend, /usr/bin/systemctl hibernate
```

```python
actions = [
    ("🔒  Lock Screen",  "loginctl lock-session"),
    ("🚪  Log Out",      "openbox --exit"),
    ("💤  Suspend",      "sudo /usr/bin/systemctl suspend"),
    ("🔁  Reboot",       "sudo /usr/bin/systemctl reboot"),
    ("⏻   Shut Down",   "sudo /usr/bin/systemctl poweroff"),
]
```

Note: `loginctl poweroff` / `loginctl reboot` do NOT exist as loginctl verbs.

## lxqt-leave centering

**Openbox window rules do NOT center lxqt-leave.** lxqt-leave sets
`Qt::X11BypassWindowManagerHint` (override-redirect) — the WM never sees the
window, so `<position force="yes">` rules are silently skipped.

Instead, use a native GTK leave dialog in launch-button.py:
```python
dlg = Gtk.Dialog(title="Session")
dlg.set_default_size(220, -1)
dlg.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
dlg.set_keep_above(True)
```
This GTK dialog is WM-managed and centers correctly on all screens.

## SNI icon parsing — service string formats

The `service` argument to `RegisterStatusNotifierItem` varies by app:

| App | service arg format | sender_name | Resolved key |
|---|---|---|---|
| nm-applet | `/org/ayatana/NotificationItem/nm_applet` | `:1.143` | `:1.143/org/ayatana/NotificationItem/nm_applet` |
| pasystray | `/org/ayatana/NotificationItem/pasystray` | `:1.144` | `:1.144/org/ayatana/NotificationItem/pasystray` |
| nm-tray   | `:1.74/StatusNotifierItem` (full key) | `:1.74` | `:1.74/StatusNotifierItem` |

Parsing:
```python
if service.startswith('/'):
    # path only — prefix with sender bus name
    key = (sender_name or '') + service
else:
    key = service   # already a full ":1.x/path" key
```

## Duplicate tray daemon pitfall

Multiple autostart .desktop files can launch tray apps redundantly, causing
duplicate icons (two WiFi icons, three sound icons) and doubled processes.

Common sources of duplicates on Galina's machine:
- `nm-tray-autostart.desktop` (system) → nm-tray (conflicts with nm-applet)
- `nm-applet.desktop` (system) → second nm-applet alongside our explicit start
- `pasystray.desktop` (system) → second pasystray alongside our explicit start
- `ayatana-indicator-application.desktop` (system) → steals SNI watcher name
- `minibar.desktop` (user) → duplicate launch-button.py if galina-panel.desktop also exists

**Fix all with Hidden=true overrides:**
```bash
for f in nm-tray-autostart nm-applet pasystray ayatana-indicator-application minibar; do
  sudo tee /home/galina/.config/autostart/${f}.desktop > /dev/null << 'EOF'
[Desktop Entry]
Hidden=true
EOF
  sudo chown galina:galina /home/galina/.config/autostart/${f}.desktop
done

# Also mask ayatana systemd user services:
sudo -u galina XDG_RUNTIME_DIR=/run/user/1000 systemctl --user mask \
  ayatana-indicator-application.service ayatana-indicators.target
```

Diagnose:
```bash
ps aux | grep -E 'nm-tray|nm-applet|pasystray|launch-button|ayatana' | grep -v grep
sudo ls /home/galina/.config/autostart/
# Check registered SNI items:
sudo -u galina DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  dbus-send --session --print-reply \
  --dest=org.kde.StatusNotifierWatcher /StatusNotifierWatcher \
  org.freedesktop.DBus.Properties.Get \
  string:'org.kde.StatusNotifierWatcher' string:'RegisteredStatusNotifierItems'
# Also verify who OWNS the watcher name:
sudo -u galina DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  dbus-send --session --print-reply \
  --dest=org.freedesktop.DBus /org/freedesktop/DBus \
  org.freedesktop.DBus.GetNameOwner string:'org.kde.StatusNotifierWatcher'
```

## Tray app startup order

The SNI watcher (launch-button.py) **must start before** tray apps and ayatana
must be dead before launch-button.py claims the watcher name.

```bash
# Kill duplicates/competitors first:
pkill -f 'launch-button.py' 2>/dev/null
pkill -x nm-tray nm-applet pasystray cbatticon 2>/dev/null
pkill -x ayatana-indicator-application-service 2>/dev/null
sleep 1

# Start watcher first:
python3 /usr/local/bin/launch-button.py &
sleep 2   # wait for SNI watcher to register on DBus

# Then tray apps:
tint2 &
sleep 1
nm-applet --no-agent &
sleep 1
pkill -x pasystray 2>/dev/null   # kill any stale from previous session
sleep 1
pasystray &
# cbatticon is XEmbed only — don't start it; use native battery label instead
```

## SNI tray app notes (Ubuntu 26.04)

| App | Protocol | Notes |
|---|---|---|
| nm-applet | SNI via libayatana-appindicator3 | `--no-agent` flag, NO XEmbed fallback |
| pasystray | SNI via libayatana-appindicator3 | SNI only |
| cbatticon | **XEmbed only** | Will NOT appear in SNI tray; use native battery label |
| nm-tray   | SNI (own watcher) | Conflicts with launch-button's watcher; replace binary |
| ayatana-indicator-application-service | SNI watcher | Steals org.kde.StatusNotifierWatcher; must be masked |

**All modern tray apps on Ubuntu 26.04 use SNI.** None fall back to XEmbed
even with `--no-indicator` flags. The only working solution is a proper SNI
host (our launch-button.py watcher).

stalonetray and tint2 systray use XEmbed only — they will never show SNI icons
without an SNI→XEmbed bridge, and snixembed is not available in Ubuntu 26.04 repos.

## Galina panel start script

Save to `/usr/local/bin/galina-panel-start.sh` (chmod +x):

```bash
#!/bin/bash
AUTH=$(find /tmp -name 'xauth_*' -user galina 2>/dev/null | head -1)
export DISPLAY=:0
export XAUTHORITY=$AUTH
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
export NO_AT_BRIDGE=1

# Kill all competing processes — ayatana FIRST (it steals the watcher name)
pkill -x ayatana-indicator-application-service 2>/dev/null
pkill -f 'launch-button.py' 2>/dev/null
pkill -x tint2 nm-tray nm-applet pasystray cbatticon 2>/dev/null
sleep 1

# 1. SNI watcher + panel (must start before tray apps)
python3 /usr/local/bin/launch-button.py &
sleep 2

# 2. Taskbar (window list only, no systray)
tint2 &
sleep 1

# 3. Tray apps — register with our watcher after it's up
nm-applet --no-agent &
sleep 1
# DO NOT kill or restart pasystray when lxqt-session supervises it.
# pkill causes lxqt-session to respawn it immediately, creating a
# registration race and duplicate icons. Leave it alone — the
# _pending_apps dedup filter in launch-button.py blocks duplicates.

# Battery handled natively in launch-button.py via /sys/class/power_supply
# cbatticon NOT started (XEmbed only, no SNI support)

wait
```
