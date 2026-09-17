# Galina Media PC — Hardened Lubuntu Build Reference

Host: HP Pavilion g6 | Ubuntu 26.04.1 LTS | LXQt | Sandy Bridge i3 | 4GB DDR3
Tailscale IP: 100.79.225.3 | SSH: admin@100.79.225.3 (passwordless sudo)

## Accounts
- `galina` — autologin, standard user, SSH key auth
- `admin` — passwordless sudo, SSH key auth, remote management only

## Boot
- GRUB: silent boot (GRUB_TIMEOUT=0, GRUB_TIMEOUT_STYLE=hidden); Shift to show menu
- SDDM autologin: User=galina, Session=Lubuntu
- Boot time: ~34s total, ~24s to graphical (was 63s)

## Key configs
- /etc/default/grub
- /etc/sddm.conf
- /home/galina/.config/lxqt/panel.conf (MUST be owned galina:galina, chmod 664)
- /home/galina/.config/picom.conf (xrender backend, vsync)
- /etc/firefox/policies/policies.json

## Firefox (native deb, no snap)
- Repo: packages.mozilla.org; Version: 154.0.1
- Policies: /etc/firefox/policies/policies.json (force-installs/blocks extensions, locks prefs)
- Profile: cedyyfvu.default-release (confirm with: sudo ls /home/galina/.mozilla/firefox/)
- user.js: /home/galina/.mozilla/firefox/cedyyfvu.default-release/user.js (applied at every startup; written by admin)
- MOZ_LOG wrapper: /usr/local/bin/firefox → logs to /home/galina/.local/share/firefox-logs/
- firefox-monitor.service: system service watching journald for OOM/crash signals
- Tab Wrangler: extension ID {0d97ff67-af49-4ef2-b285-d87ad0bd1981} (was force-installed; check extensions/ dir)
- Auto Tab Discard: extension ID {c2c003ee-bd69-42a2-b0e9-6f34222cb046} — BLOCKED via policy
  Was force-installed; caused Firefox to close during movies (discarded the playing tab as 'idle').
  Policy now sets installation_mode: "blocked"; XPI and storage removed from profile.

### Firefox closes during movie — diagnostic order
Run through these in order; stop at the one that matches:
1. **earlyoom kill** — Firefox exits completely, RAM jumps to 90% immediately after; see earlyoom section below.
2. **Tab Discard/extension** — Firefox running, video tab gone or blank; check extensions.json and policies.json.
3. **X11 visibility suspend** — Firefox running, video frozen; decoder entered Suspend state; see visibility section.
4. **Lid-close / power event** — check `lidClosedAcAction` in lxqt-powermanagement.conf; action=4 means screen-off only (safe), action=1 means suspend (kills video).

**Pitfall: force-installed extensions can be ACTIVE even after profile disables them.**
An extension with `installation_mode: force_installed` in policies.json will be re-activated
by Firefox on every startup, overriding userDisabled=True in extensions.json. The only
reliable block is changing to `installation_mode: blocked` in the policy file itself.
Do NOT rely on extensions.json `userDisabled` or `active` field alone — check policies.json first.

**Check extensions.json for the ACTIVE field, not just presence:**
```
python3 -c "
import json
with open('/home/galina/.mozilla/firefox/cedyyfvu.default-release/extensions.json') as f:
    d = json.load(f)
for a in d.get('addons', []):
    print(a.get('defaultLocale',{}).get('name'), '| active:', a.get('active'), '| userDisabled:', a.get('userDisabled'))
"
```
An extension can be ACTIVE:True even when userDisabled:False — the policy overrides user state.

**Check policy file** for force-installed extensions and which prefs are locked:
```
cat /etc/firefox/policies/policies.json
```
If an extension has `installation_mode: force_installed`, it will be active regardless of profile state.
To permanently block it: change to `installation_mode: blocked`, remove its XPI from the profile,
and delete its storage directory under `~/.mozilla/firefox/<profile>/storage/default/moz-extension+++<uuid>*/`.

### Firefox abrupt exit during video (earlyoom kill)
**Symptom:** Firefox closes mid-movie with no crash report, no segfault in dmesg; earlyoom log
shows available RAM dropping to 59-69% during playback, then jumping back to 90% after exit.
**Root cause:** earlyoom configured with `--prefer firefox`, making Firefox the first kill
candidate under any memory pressure. With Gmail + video playing, earlyoom kills Firefox
before memory is actually critical.
**Diagnostic:**
```
sudo journalctl -u earlyoom --since '2 hours ago' | tail -40
# Look for: mem avail dropping to 60-70% bracketing the exit time, then jumping back
# If free RAM recovers instantly after Firefox disappears = earlyoom kill, not OOM/crash
```
**Fix:** Move Firefox from `--prefer` to `--avoid` in /etc/default/earlyoom:
```
EARLYOOM_ARGS="-r 60 -m 8,4 -s 10,5 -p --avoid '(^|/)(Xorg|lxqt|openbox|sshd|firefox|Isolated[[:space:]]Web[[:space:]]Co)$'"
```
Write with `sudo tee /etc/default/earlyoom`, then `sudo systemctl restart earlyoom`.
Do NOT use sed on this file — the bracket expressions and pipes defeat shell escaping reliably.
**Pitfall:** earlyoom's `--prefer` regex targets both the `firefox` process AND `Isolated Web Co`
(content processes). Adding only `firefox` to --avoid still allows content process kills;
include both in the pattern.

### Firefox background tab memory — user.js settings
For a 4GB machine doing video playback + Gmail simultaneously, add to user.js:
```
user_pref("browser.tabs.unloadOnLowMemory", true);
user_pref("browser.low_commit_space_threshold_mb", 600);
user_pref("browser.low_commit_space_threshold_percent", 20);
user_pref("browser.tabs.min_inactive_duration_before_unload", 300000);
user_pref("browser.sessionstore.interval", 60000);
user_pref("browser.sessionstore.resume_from_crash", true);
```
Chown to galina:galina after writing as admin.

### Firefox policy — locking media prefs (canonical set)
All these should be in /etc/firefox/policies/policies.json under `Preferences` with `Status: locked`.
Locking via policy is more reliable than mozilla.cfg alone (policy wins on any pref clash):
```json
"media.suspend-background-video.enabled": {"Value": false, "Status": "locked"},
"media.dormant-on-pause-timeout-ms": {"Value": -1, "Status": "locked"},
"media.block-autoplay-until-in-foreground": {"Value": false, "Status": "locked"},
"media.autoplay.default": {"Value": 0, "Status": "locked"},
"media.autoplay.blocking_policy": {"Value": 0, "Status": "locked"},
"media.shutdown-delay-ms": {"Value": 0, "Status": "locked"},
"browser.tabs.closeWindowWithLastTab": {"Value": false, "Status": "locked"}
```
`browser.tabs.closeWindowWithLastTab: false` prevents Firefox window from closing entirely
when a tab is discarded/closed — critical safety net when Tab Discard-style extensions are present.

**Pitfall:** mozilla.cfg and /etc/firefox/policies/policies.json can coexist, but only
prefs listed in policies.json under `Preferences` are truly locked via the enterprise API.
Prefs only in mozilla.cfg via `lockPref()` can be shadowed by extension storage. Add all
critical media prefs to policies.json; treat mozilla.cfg as a fallback/redundant layer.

### Firefox video stops mid-movie (X11 visibility suspend)
**Symptom:** Video playing on kinogo.li (or similar) stops abruptly mid-movie with no crash.
**Root cause:** Firefox media decoder responds to repeated `ApproximatelyNonVisible`
visibility events. On X11 dual-display setups, the compositor briefly marks the Firefox
window as non-visible during panel redraws or focus shifts. The final `docHidden=true`
flip does not recover — decoder enters Suspend state, video stops.

**Distinguish from earlyoom kill first** (see section above): earlyoom kill = RAM jumps
back to 90% the instant Firefox exits; video stops AND Firefox is gone. Visibility suspend
= Firefox keeps running, video just freezes.

**Diagnostic path:**
1. Check earlyoom journal: `sudo journalctl -u earlyoom --since '2 hours ago' | tail -40`
   If RAM recovers immediately when Firefox closes = earlyoom kill (fix that first).
   If Firefox is still running after video freezes = visibility suspend.
2. Check MOZ_LOG child log: `grep -a 'docHidden\|Visibility\|Suspend' /home/galina/.local/share/firefox-logs/<latest>.child-1.moz_log | strings | tail -60`
   Repeated `ApproximatelyNonVisible` / `docHidden=true` cycles confirm the cause.

**Fix (user.js — takes effect on next Firefox restart):**
```
user_pref("media.suspend-background-video.enabled", false);
user_pref("media.suspend-background-video.delay-ms", 0);
user_pref("media.block-autoplay-until-in-foreground", false);
user_pref("media.dormant-on-play-n-seconds", -1);
user_pref("dom.timeout.background_throttling_max_budget", -1);
user_pref("dom.timeout.enable_budget_timer_throttling", false);
```
Galina must close and reopen Firefox after editing user.js.

**Pitfall:** galina's user cannot see system journal (not in adm/systemd-journal groups).
Always use `sudo journalctl` for system-level crash/signal/OOM investigation.

## X11 cursor disappears
**Symptom:** Mouse cursor invisible system-wide — not just in one app; moving the mouse shows
no cursor on screen. Can happen after fullscreen video exit, picom restart, or display mode change.

**Quick fix (SSH — takes effect immediately):**
```bash
XAUTH=$(find /tmp -name 'xauth_*' -user galina 2>/dev/null | head -1)
DISPLAY=:0 XAUTHORITY=$XAUTH xsetroot -cursor_name left_ptr
```
This resets the root window cursor to the standard arrow. The cursor becomes visible on
next mouse move without requiring a restart.

**If xsetroot alone doesn't help:** also wiggle the mouse position via xdotool:
```bash
DISPLAY=:0 XAUTHORITY=$XAUTH xdotool mousemove 100 100
DISPLAY=:0 XAUTHORITY=$XAUTH xdotool mousemove 500 400
```

**Diagnostic:** Check whether a compositor (picom/xcompmgr) or `unclutter` is hiding it:
```bash
pgrep -a 'picom|xcompmgr|compton|unclutter'
```
If unclutter is running, it hides the cursor after idle — kill it or remove from autostart.
This machine has no compositor running by default; cursor hide is typically a CSS `cursor: none`
left over from a fullscreen video player that crashed or was force-killed.

**Cursor theme:** Breeze_Light, size 30px. Config locations:
- ~/.Xresources: `Xcursor.size: 30`
- ~/.config/lxqt/lxqt.conf: `cursor_size=30`
- gsettings: `org.gnome.desktop.interface cursor-theme 'Breeze_Light'`
If the theme breaks: `DISPLAY=:0 XAUTHORITY=$XAUTH xsetroot -cursor_name left_ptr` falls
back to the built-in X11 cursor regardless of theme state.

## Performance
- snapd purged (saves ~10-15s boot, ~150MB RAM)
- ZRAM 1.9GB lzo-rle; BFQ scheduler; swappiness=10
- Disabled: blueman, cups, avahi, ModemManager, system-config-printer,
  lubuntu-update-notifier, lxqt-runner, thermald, gpu-manager
- Idle RAM: ~468MB (was 823MB)

## WiFi (Ralink RT5390)
- /etc/NetworkManager/conf.d/wifi-powersave.conf (powersave=2)
- /etc/modprobe.d/rt2800pci.conf (nohwcrypt=1)

## Automation
- Cleanup: /etc/cron.daily/galina-cleanup (30-day file deletion)
- HDMI hotplug: /etc/udev/rules.d/95-hdmi-hotplug.rules + /usr/local/bin/hdmi-hotplug.sh
- Panel watchdog: /etc/cron.d/galina-panel-watchdog (every 5 min, root)
  Restarts launch-button.py and galina-media-inhibit.sh if down
- Media inhibit: /usr/local/bin/galina-media-inhibit.sh
  Runs as galina, checks every 4 min; resets xset s + xdg-screensaver when Firefox/VLC running
- galina-panel-watchdog log: /var/log/galina-panel-watchdog.log

**Pitfall:** Stale /etc/cron.d/ entries whose scripts have been deleted still run every cycle
and produce journal noise. Audit with `ls /etc/cron.d/` and check each script path exists;
remove orphaned entries with `sudo rm /etc/cron.d/<name>`.

## Panel failure lessons (2026-09-01, session 1)
- Root cause of 1x1 panel: panel.conf written by root (sudo tee) without chown fix
- lxqt-panel 2.3 needs panels=panel1 at top AND type= in each plugin section
- chattr +i on panel.conf is fatal: blocks lxqt-panel/lxqt-session state writes
- nm-tray provides StatusNotifierWatcher D-Bus name for tray: do not remove or kill it
- picom backend (glx/xrender) does NOT cause the 1x1 bug (tested both)
- Multiple stale panel instances stack up during manual restarts: always pkill -9 first

## Panel failure lessons (2026-09-01, session 2 — continued debugging)
- lxqt-session OVERWRITES panel.conf on every boot, adding [General] + __userfile__=true;
  this is normal and harmless IF the file is writable (664) and the plugin config survives
- Do NOT pre-write __userfile__=true or [General] in a hand-crafted config; lxqt-panel
  may reject the file as invalid if the content doesn't match expected format
- The correct SNI plugin for Lubuntu 26.04 is `statusnotifier`, not `tray` alone;
  using only `tray` can cause the panel to self-close on startup
- Manual nm-tray restarts via sudo leave stale X11 dock windows (window IDs persist);
  these register into the tray plugin on next panel start and trigger `closing`;
  always prefer reboot over manual cycling of tray processes
- lxqt-panel started manually (outside lxqt-session) reliably produces 1x1 windows;
  the panel must be started by lxqt-session to size correctly — session ordering matters
- Emergency xdotool fix works per-session: `xdotool windowsize $DECID 1366 28` then
  `xdotool windowmove $DECID 0 740` (install: sudo apt-get install -y xdotool)
- QT_SCREEN_SCALE_FACTORS="" appears in debug log but is cosmetic; not the 1x1 cause
- wmctrl cannot resize unmanaged panel windows (no _NET_WM_MOVERESIZE support)
- Root 1x1 cause on this system: UNRESOLVED — xdotool resize is the current workaround
