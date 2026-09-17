# HDMI Mirror Mode with Mixed Resolutions

**Session date:** 2026-09-02  
**Context:** Galina's laptop (1366x768 LVDS-1) + TV (1920x1080 HDMI-1)

## The problem

xrandr cannot natively run two outputs at different resolutions in true mirror/clone
mode — `--same-as` requires a common resolution. The usual "set both to 1920x1080"
downscales the laptop panel and looks blurry.

## Working solution: --scale-from

Run each output at its native resolution, but use `--scale-from 1920x1080` on the
laptop so its 1366x768 framebuffer is scaled up to fill the shared 1920x1080 logical
area. Both outputs position at `0x0` (same-as / mirror).

```bash
sudo -u galina DISPLAY=:0 xrandr \
  --output HDMI-1 --mode 1920x1080 --rate 60 --pos 0x0 --primary \
  --output LVDS-1 --mode 1366x768 --rate 59.99 --pos 0x0 --scale-from 1920x1080 \
  --output VGA-1 --off \
  --output DP-1 --off
```

Result:
- TV: native 1920x1080, crisp
- Laptop screen: 1366x768 panel upscaled to 1920x1080 framebuffer (slight softness, acceptable)
- Framebuffer: 1920x1080

To revert (HDMI disconnected, laptop only):
```bash
sudo -u galina DISPLAY=:0 xrandr \
  --output LVDS-1 --mode 1366x768 --rate 59.99 --pos 0x0 --scale 1x1 --primary \
  --output HDMI-1 --off
```

## Pitfall: xrandr resolution change breaks lxqt-panel / tint2

Changing the framebuffer size mid-session (e.g. 3286x1080 extended → 1920x1080 mirror)
confuses running panel instances. tint2 may resize correctly but lxqt-panel can
become stuck or fail to launch against the new geometry.

**Fix:** Restart the panel stack after xrandr changes:
```bash
sudo kill $(pgrep -d' ' 'tint2|lxqt-panel')
sleep 2
sudo -u galina DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  /usr/local/bin/galina-panel-start.sh &
```

The panel watchdog cron (5-minute interval) will also auto-recover if the panel
drops after xrandr changes.

## Persistent hotplug automation (udev)

File: `/etc/udev/rules.d/99-hdmi-mirror.rules`
```
ACTION=="change", KERNEL=="card0", SUBSYSTEM=="drm", RUN+="/usr/local/bin/hdmi-display-setup.sh"
```

File: `/usr/local/bin/hdmi-display-setup.sh`
```bash
#!/bin/bash
export DISPLAY=:0
AUTH=$(find /tmp -maxdepth 1 -name 'xauth_*' -user galina 2>/dev/null | head -1)
[ -n "$AUTH" ] && export XAUTHORITY="$AUTH"

CONNECTED=$(xrandr 2>/dev/null | grep 'HDMI-1 connected')

if [ -n "$CONNECTED" ]; then
  # HDMI plugged in — mirror mode
  xrandr --output HDMI-1 --mode 1920x1080 --rate 60 --pos 0x0 --primary \
         --output LVDS-1 --mode 1366x768 --rate 59.99 --pos 0x0 --scale-from 1920x1080
else
  # HDMI unplugged — laptop only
  xrandr --output LVDS-1 --mode 1366x768 --rate 59.99 --pos 0x0 --scale 1x1 --primary \
         --output HDMI-1 --off
fi

# Restart panel to adapt to new framebuffer geometry
sleep 1
sudo -u galina DISPLAY=:0 \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  /usr/local/bin/galina-panel-start.sh &
```

Make executable: `sudo chmod +x /usr/local/bin/hdmi-display-setup.sh`  
Reload rules: `sudo udevadm control --reload-rules`

## Display output names on Galina's Sandy Bridge system

| Output | Description |
|---|---|
| LVDS-1 | Laptop panel (built-in), 1366x768 |
| HDMI-1 | HDMI port → living room TV, max 1920x1080 |
| VGA-1 | VGA port (unused) |
| DP-1 | DisplayPort (unused) |
