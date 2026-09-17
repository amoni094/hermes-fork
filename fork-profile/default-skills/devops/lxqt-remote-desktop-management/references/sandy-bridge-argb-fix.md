# Sandy Bridge i915 + LXQt Panel ARGB Fix

## Problem

On hardware with Sandy Bridge i915 GPU, picom (v12.5) cannot install an ARGB
(32-bit depth) colormap. lxqt-panel requests an ARGB visual for transparency;
picom fails to provide it; panel hangs in a 1x1+0+0 state or crashes immediately
with:

    error 140: BadRegion request 138 minor 14 (XFixesSetRegion failure)

picom's ARGB colormap failure is silent — `picom -b` may exit 0 but leave no
compositor running. Verifying compositor presence:

```bash
AUTH=$(ls /tmp/xauth_* 2>/dev/null | head -1)
sudo -u galina DISPLAY=:0 XAUTHORITY=$AUTH xprop -root _NET_WM_CM_S0
# Returns WINDOW if compositor claims the slot; 'not found' = no compositor
```

## Root Cause Chain

1. picom claims `_NET_WM_CM_S0` X selection (compositor slot)
2. Attempts ARGB colormap install — fails on Sandy Bridge i915 at driver level
3. lxqt-panel requests compositor-backed ARGB visual
4. Panel calls `XFixesSetRegion` → BadRegion because region IDs were never
   properly allocated under the failed ARGB colormap
5. Panel crashes, lxqt-session respawns it → infinite crash loop at 84-99% CPU

## Fix: Force Qt native X11 painting

Set these two env vars before launching lxqt-panel:

```bash
export QT_XCB_NATIVE_PAINTING=1   # forces X11 native rendering, bypasses ARGB/compositor path
export QT_X11_NO_MITSHM=1         # disables MIT-SHM for older GPU compatibility
```

Panel renders solid (opaque) instead of transparent — acceptable tradeoff.
No compositor required. No BadRegion errors.

Verify these are set inside the running panel process:
```bash
PANEL_PID=$(pgrep -f '/usr/bin/lxqt-panel' | head -1)
sudo cat /proc/$PANEL_PID/environ | tr '\0' '\n' | grep QT
```

## Wrapper Script Pattern

Do NOT set these in `~/.profile` alone — lxqt-session caches its env at login
and may launch panel before profile exports are active. Use a wrapper:

```bash
# /usr/local/bin/lxqt-panel-wrapped
#!/bin/bash
# Find XAUTHORITY dynamically (changes each boot)
AUTH=$(find /tmp /run/sddm -maxdepth 1 -name 'xauth_*' -user galina 2>/dev/null | head -1)

# Inherit session env (XDG_MENU_PREFIX, XDG_DATA_DIRS, DBUS path) from lxqt-session
SESSION_PID=$(pgrep -u galina lxqt-session | head -1)
if [ -n "$SESSION_PID" ]; then
    eval $(sudo cat /proc/$SESSION_PID/environ | tr '\0' '\n' | \
           grep -E '^(XDG_MENU_PREFIX|XDG_DATA_DIRS|XDG_CONFIG_DIRS|DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR)=' | \
           sed 's/^/export /')
fi

export DISPLAY=:0
export XAUTHORITY=$AUTH
export QT_XCB_NATIVE_PAINTING=1
export QT_X11_NO_MITSHM=1

exec /usr/bin/lxqt-panel
```

Register this wrapper:
```bash
sudo chmod +x /usr/local/bin/lxqt-panel-wrapped
# In /etc/xdg/autostart/lxqt-panel.desktop:
# Exec=/usr/local/bin/lxqt-panel-wrapped
# X-LXQt-Module=false   <- CRITICAL: prevents lxqt-session crash-restart loop
```

## Stop lxqt-session Respawning Crashed Panel

`X-LXQt-Module=true` in the panel's autostart `.desktop` file makes lxqt-session
supervise and restart it on crash. With the crash loop active this means
instant re-launch → crash → re-launch at 84% CPU.

Fix: set `X-LXQt-Module=false` in BOTH:
- `/etc/xdg/autostart/lxqt-panel.desktop` (system-wide)
- `/home/galina/.config/autostart/lxqt-panel.desktop` (user override, if exists)

The user override file takes precedence over the system file when both exist.

## BadRegion Error Source Disambiguation

Multiple processes generate BadRegion (XFixes) errors simultaneously. Not all
are from lxqt-panel:

- `pcmanfm-qt` (desktop file manager) generates continuous BadRegion errors
  at ~54/second from its desktop window rendering — **harmless, ignore these**
- Genuine panel BadRegion errors are only present when panel is crashing;
  once QT_XCB_NATIVE_PAINTING=1 is set, panel stops generating them entirely

Tell them apart by: kill lxqt-panel and observe if the flood continues (yes =
pcmanfm-qt source, not panel).

## fancymenu Inotify Loop Bug (lxqt-panel 2.3.x on Ubuntu 26.04)

On Ubuntu 26.04 with lxqt-panel 2.3.x, the `fancymenu` plugin enters a tight
inotify loop reading `~/.config/user-dirs.dirs` and rebuilding the app list.
This produces 84-99% CPU even when the panel is otherwise rendering correctly.

Diagnose:
```bash
strace -p $(pgrep lxqt-panel) -e trace=read,inotify_add_watch 2>&1 | head -30
# Flood of read() on the user-dirs file = fancymenu inotify loop
```

**Fix: switch to `mainmenu` plugin** (hierarchical menu, no inotify, compiled-in):

In `/home/galina/.config/lxqt/panel.conf`, change the plugins line:
```ini
# Before:
plugins=fancymenu,spacer,taskbar,spacer,statusnotifier,worldclock

# After:
plugins=mainmenu,spacer,taskbar,spacer,statusnotifier,worldclock
```

Remove the `[fancymenu]` section. Add `[mainmenu]` if needed (optional, defaults work).
mainmenu is a static plugin (compiled into the binary), available in all
lxqt-panel 2.3.x packages on Ubuntu 26.04.

## XDG Env Vars: Why the App Menu is Empty

When launching lxqt-panel via `sudo -u galina ... /usr/bin/lxqt-panel` from SSH,
the process does NOT inherit the user session's XDG environment:

| Missing var | Effect |
|---|---|
| `XDG_MENU_PREFIX` (expected: `lxqt-`) | fancymenu/mainmenu looks for `applications.menu` (no prefix), not `lxqt-applications.menu` → no app list |
| `XDG_DATA_DIRS` (expected: `/usr/share/Lubuntu:/usr/local/share/:/usr/share/`) | Plugin can't find `.desktop` files → empty search |

Fix: inherit these from lxqt-session's `/proc/$PID/environ` (see wrapper script above).

DO NOT set `XDG_DATA_DIRS` to a broader path than the session default —
adding extra dirs (e.g. `/usr/share/xdg`) triggers more inotify watches
and worsens the fancymenu CPU loop.

## StatusNotifier Tray Daemons: Restart Ordering

StatusNotifierItem (SNI) tray daemons (`nm-tray`, `lxqt-powermanagement`) must
registered with the panel's `StatusNotifierWatcher` AFTER the panel is fully up.
Daemons started before the panel (normal session boot order) work fine. Daemons
restarted during panel debugging often fail to re-register.

Fix: in the wrapper, sleep 8-10s after panel starts, then restart powermanagement:

```bash
slash /usr/bin/lxqt-panel &
PANEL_PID=$!
sleep 10
# Re-register battery tray
pkill -u galina lxqt-powermanagement 2>/dev/null
sudo -u galina DISPLAY=:0 XAUTHORITY=$AUTH DBUS_SESSION_BUS_ADDRESS=$DBUS \
    nohup lxqt-powermanagement >/dev/null 2>&1 &
```

Verify registration:
```bash
DBUS=$DBUS_SESSION_BUS_ADDRESS
sudo -u galina DBUS_SESSION_BUS_ADDRESS=$DBUS \
    busctl call org.kde.StatusNotifierWatcher \
    /StatusNotifierWatcher org.kde.StatusNotifierWatcher \
    RegisteredStatusNotifierItems 2>/dev/null
# Should return 3+ items: network, volume, battery
```

## Orphaned Wrapper Shell Processes

When launching via `sudo -u galina ... lxqt-panel-wrapped & ` from SSH scripts,
the parent bash shell stays alive after lxqt-panel exits. This orphaned shell
holds an X connection and generates BadRegion errors until it times out.

Fix: always launch via `setsid` to fully detach from the SSH session, and use
`exec` inside the wrapper script so bash is replaced by lxqt-panel (no orphan):

```bash
# Launching from SSH:
sudo -u galina setsid /usr/local/bin/lxqt-panel-wrapped </dev/null >/tmp/panel.log 2>&1 &

# Inside the wrapper, always use exec for the final launch:
exec /usr/bin/lxqt-panel
```

## Qt6/XCB XI2 Input Grab: Click Failures

Separate from the ARGB/picom issue. Even after fixing ARGB (with native painting
or Composite disabled), mouse clicks on panel buttons may silently fail.

### Root cause

Qt6's XCB platform always creates a **native container window** (unnamed parent
of the real panel widget) that selects ButtonPress via XInput2 (XI2) device
grabs. Core X event delivery hits the container; the container uses XI2 event
selection (not the core `your_event_mask`) so the standard `xwininfo -events`
shows ButtonPress, but `python3-xlib`'s `get_attributes().your_event_mask`
returns 0 — the grab is at the XI2 layer, invisible to core X inspection.

### Reliable fix: disable Composite extension

When Composite is disabled, Qt6 cannot use ARGB and falls back to depth-24 for
all windows including the container. Depth-24 container windows route clicks
correctly without the XI2 detour:

```bash
# Create /etc/X11/xorg.conf.d/99-no-composite.conf:
Section "Extensions"
    Option "Composite" "Disable"
EndSection
```

Requires X server restart (reboot). Verified working: depth-24 container,
clicks pass through to panel widgets.

### What does NOT fix it

| Attempt | Why it fails |
|---|---|
| `QT_XCB_NATIVE_PAINTING=1` | Doesn't prevent container creation |
| `QT_XCB_NO_XI2=1` | Qt6 may ignore this env var on some build configs |
| `QT_AUTO_SCREEN_SCALE_FACTOR=0` | Unrelated to XI2 grab |
| Patching container's core event mask via python3-xlib | XI2 is separate from core; `change_attributes(event_mask=0)` does nothing |
| `xdotool click` from SSH | Synthetic XSendEvent is not delivered to Qt6 widgets; cannot test clicks remotely |

### Testing limitation

`xdotool click` sends synthetic X events (`XSendEvent`). Qt6 button widgets
**ignore synthetic events** for security reasons. This means:
- You CANNOT verify start button click works using xdotool from SSH
- A test showing menu didn't open after `xdotool click` does NOT mean clicking is broken
- Only the user's physical mouse click is a valid test of panel interactivity

## Ghost Composite Manager Window

When xcompmgr or picom crashes uncleanly, they may leave a ghost X window
holding the `_NET_WM_CM_S0` selection. New compositor instances see
"Another composite manager is already running" and exit immediately.

Detect:
```python
import Xlib.display
d = Xlib.display.Display(':0')
owner = d.get_selection_owner(d.intern_atom('_NET_WM_CM_S0'))
print(hex(owner.id))  # non-zero = ghost holding selection
```

Note: lxqt-panel itself calls `XCompositeRedirectSubwindows` on its windows,
which is a separate Composite extension lock from `_NET_WM_CM_S0`. Even after
destroying the ghost window, lxqt-panel's redirect lock can prevent xcompmgr
from starting.

**Best fix on Sandy Bridge**: disable Composite entirely (see above) rather
than fighting ghost windows and compositor restart races.

## Hardware Reference

- GPU: Sandy Bridge i915 (Intel 2nd Gen, circa 2011-2012)
- Screen: 1366x768
- OS: Ubuntu 26.04 (Lubuntu/LXQt)
- lxqt-panel: 2.3.x
- picom: 12.5 (incompatible with ARGB on this GPU — disable or replace)
- xcompmgr: lightweight alternative; unreliable on Sandy Bridge due to panel's
  own Composite redirect; disable Composite entirely instead
- python3-xlib: 0.33 (available via apt; needed for X window inspection scripts)
