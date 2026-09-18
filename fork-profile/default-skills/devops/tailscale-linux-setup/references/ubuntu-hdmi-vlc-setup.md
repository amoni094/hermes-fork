# Ubuntu HDMI + VLC Setup (Sandy Bridge / Intel iGPU)

Validated on: galina-hppaviliong6notebookpc, Ubuntu 26.04 LTS, Intel Sandy Bridge (2nd Gen Core)

## Driver Stack Verification

    lspci | grep -E 'VGA|Display|3D|GPU'
    lsmod | grep -E 'i915|amdgpu|nouveau|radeon|nvidia'
    sudo dmesg | grep -i hdmi | tail -10

For Sandy Bridge: expect `i915` loaded, and `HDA Intel PCH HDMI/DP` in dmesg.

## Required Packages (Ubuntu 26.04)

All of these are pre-installed on Ubuntu 26.04 — verify before installing:

    dpkg -l | grep -E 'intel-media-va-driver|xserver-xorg-video-intel|mesa|vainfo'

Key packages:
- `xserver-xorg-video-intel` — Intel DDX driver
- `intel-media-va-driver` — iHD VA-API driver (Sandy Bridge uses i965 fallback, not iHD)
- `linux-firmware-intel-graphics` — GPU firmware
- `mesa-vulkan-drivers`, `libgl1-mesa-dri` — Mesa stack
- `ubuntu-restricted-extras` — proprietary codecs (mp3, aac, ac3, dts, h264)
- `gstreamer1.0-plugins-bad`, `gstreamer1.0-plugins-ugly`, `gstreamer1.0-libav` — codec backends
- `vlc-plugin-fluidsynth` — MIDI support

## VA-API Check

    sudo apt install -y vainfo
    vainfo 2>&1

Sandy Bridge will use the `i965` driver (not `iHD`). Expected output:

    Driver version: Intel i965 driver for Intel(R) Sandybridge Mobile
    VAProfileH264ConstrainedBaseline: VAEntrypointVLD + VAEntrypointEncSlice
    VAProfileH264High: VAEntrypointVLD + VAEntrypointEncSlice
    VAProfileMPEG2Simple/Main: VAEntrypointVLD

## VLC Configuration for TV Playback

Apply via Python script to handle both fresh installs and existing vlcrc:

    python3 << 'EOF'
    import os, re
    vlcrc = os.path.expanduser('~/.config/vlc/vlcrc')
    settings = {
        'avcodec-hw': 'vaapi',           # hardware decode via VA-API
        'deinterlace': '0',              # auto-deinterlace
        'deinterlace-mode': 'yadif2x',   # best quality if triggered
        'fullscreen': '1',               # default fullscreen for TV use
        'mouse-hide-timeout': '3000',    # hide cursor after 3s
        'avcodec-skiploopfilter': '0',   # full quality decode
    }
    os.makedirs(os.path.dirname(vlcrc), exist_ok=True)
    content = open(vlcrc).read() if os.path.exists(vlcrc) else ''
    for key, val in settings.items():
        pattern = rf'^#?{re.escape(key)}=.*$'
        replacement = f'{key}={val}'
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            content += f'\n{key}={val}'
    open(vlcrc, 'w').write(content)
    print('vlcrc updated')
    EOF

Run remotely:

    ssh -o BatchMode=yes galina@100.79.225.3 "python3 << 'PYEOF'\n...(script)...\nPYEOF"

## HDMI Audio Gotcha

Audio output does NOT automatically switch to HDMI on plug-in. User must:
1. Plug in HDMI cable
2. Open Sound Settings
3. Switch output to "HDA Intel PCH HDMI" (or similar)

This cannot be preset remotely — it requires the TV to be connected at config time.
Alternatively, PulseAudio/PipeWire can be scripted: `pactl set-default-sink <hdmi-sink>`
but the sink name varies per TV — not practical to pre-configure.

## Unattended Upgrades (Ubuntu)

Check status:

    systemctl is-enabled unattended-upgrades
    cat /etc/apt/apt.conf.d/20auto-upgrades

Fully configured state:

    APT::Periodic::Update-Package-Lists "1";
    APT::Periodic::Unattended-Upgrade "1";

Auto-reboot is NOT enabled by default (safe). To enable silent reboot after kernel updates:

    # In /etc/apt/apt.conf.d/50unattended-upgrades:
    Unattended-Upgrade::Automatic-Reboot "true";
    Unattended-Upgrade::Automatic-Reboot-Time "03:00";

## Large Remote apt Installs

Snap and large apt installs (e.g. ubuntu-restricted-extras) take 3-5 minutes.
Use `terminal(background=True, notify=True)` to avoid timeout:

    terminal(
        command='ssh -o BatchMode=yes galina@100.79.225.3 "sudo DEBIAN_FRONTEND=noninteractive apt install -y <pkgs> 2>&1"',
        background=True,
        notify=True
    )

Then `process(action='wait', session_id=..., timeout=300)` to collect output.
DEBIAN_FRONTEND=noninteractive suppresses all interactive prompts.

## Hardware Diagnostic (Old Hardware)

Full hardware health check for old Ubuntu laptops:

    # Install tools
    sudo apt install -y smartmontools lm-sensors vainfo

    # CPU temps
    sudo sensors-detect --auto; sensors

    # Disk SMART health
    sudo smartctl -a /dev/sda

    # Fan/thermal dmesg errors
    sudo dmesg | grep -iE 'fan|thermal|temperature|overheat|hp-wmi' | tail -20

    # General hardware errors
    sudo dmesg | grep -iE 'error|fail' | grep -v 'acpi\|pci\|NET\|IPv\|audit' | tail -20

### Known HP Pavilion G6 / hp-wmi Fan Error

    hp-wmi: Failed to apply initial fan settings: -22

This is a cosmetic boot error. The hp-wmi Linux driver tries to set fan speed via WMI
at boot but the Sandy Bridge-era HP BIOS doesn't expose that WMI interface. The fan is
working — temperatures confirm it. Safe to ignore. Not fixed by BIOS update.

### BIOS Update Decision for HP Pavilion G6

- Current: F.42 (Dec 2011). Latest available: F.48 or F.49 (2012).
- Updates between F.42 and F.49 were Windows-specific (sleep/hibernate, battery reporting).
- linux-firmware and intel-microcode packages in Ubuntu cover all microcode updates more
  current than any HP BIOS release. No Linux benefit from flashing.
- Flash process requires Windows .exe or DOS USB tool — high brick risk on spinning HDD.
- Verdict: skip BIOS update on this hardware.

## Performance Optimisation (Old HDD Laptop)

For Sandy Bridge / 5400 RPM HDD laptops with 4GB RAM on Ubuntu:

### Install

    sudo apt install -y zram-config earlyoom tlp tlp-rdw

### Configure swappiness (prefer RAM, avoid HDD thrashing)

    echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf
    echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.d/99-swappiness.conf
    sudo sysctl -p /etc/sysctl.d/99-swappiness.conf

### BFQ disk scheduler (better interactivity on HDD)

    echo 'ACTION=="add|change", KERNEL=="sda", ATTR{queue/scheduler}="bfq"' | \
      sudo tee /etc/udev/rules.d/60-scheduler.rules

### earlyoom config (prevent freeze before OOM killer fires)

    sudo sed -i 's/^EARLYOOM_ARGS=.*/EARLYOOM_ARGS="-r 60 -m 10 -s 10"/' /etc/default/earlyoom
    sudo systemctl restart earlyoom

### Start TLP

    sudo tlp start

Note: do NOT install preload on low-RAM HDD systems — its boot penalty (22s+) exceeds
its benefit when RAM is constrained. It works better on systems with 8GB+ RAM.

## Boot Time Optimisation (Ubuntu on HDD)

Diagnose with:

    systemd-analyze
    systemd-analyze blame | head -20
    systemd-analyze critical-chain | head -30

### Common culprits on old Ubuntu laptops and fixes

| Service | Time | Fix |
|---|---|---|
| apport.service | 30s | `sudo systemctl disable apport.service` — crash reporter, useless on desktop |
| grub2-common.service | 29s | `sudo systemctl disable grub2-common.service` — runs grub hooks every boot unnecessarily |
| preload.service | 22s | `sudo systemctl disable preload.service` — boot cost > benefit on low RAM |
| networkd-dispatcher | 20s | `sudo systemctl disable networkd-dispatcher.service` — redundant with NetworkManager |
| e2scrub_reap.service | 36s | `sudo systemctl disable e2scrub_reap.service` — filesystem check, not needed on desktop |
| blueman-mechanism | 25s | `sudo systemctl disable blueman-mechanism.service` — if Bluetooth not needed |

HDD spin-up (dev-sda.device ~20s) is a hardware floor — cannot be reduced in software.
An SSD upgrade is the single largest possible boot improvement (60s -> ~8s total).

### Snap bloat reduction

Each installed snap adds 1-2 squashfs mounts to boot. Audit installed snaps:

    snap list

Remove redundant ones (e.g. Firefox if Chromium is installed, firmware-updater if fwupd
doesn't support the hardware):

    sudo snap remove firefox
    sudo snap remove firmware-updater

Snap removal is slow (60s+) — run in background:

    terminal(command='ssh ... "sudo snap remove firefox"', background=True, notify=True)

Note: snap remove operations lock snapd — run sequentially, not in parallel.
Wait for one to complete before starting the next (use sleep or process wait).

### Fedora Silverblue (this machine) — different profile

Fedora Silverblue with NVMe + 32GB RAM needs almost none of the above:
- ZRAM already active
- NVMe makes scheduler tuning irrelevant
- RAM is ample — earlyoom/preload unnecessary
- Only worthwhile tweak: swappiness 60 -> 10 (prefer RAM over NVMe swap)
- fwupd.service adds ~25s — mask if not needed: `sudo systemctl mask fwupd.service`

## Remote User Account Management

### Create a privileged admin account, demote regular user

    # Create admin with all relevant groups
    sudo useradd -m -s /bin/bash -G adm,cdrom,sudo,dip,plugdev,lpadmin,sambashare admin
    echo 'admin:PASSWORD' | sudo chpasswd

    # Remove regular user from sudo and adm
    sudo deluser galina sudo
    sudo deluser galina adm

    # Copy SSH authorized_keys so agent can SSH as admin
    sudo mkdir -p /home/admin/.ssh
    sudo cp /home/galina/.ssh/authorized_keys /home/admin/.ssh/
    sudo chown -R admin:admin /home/admin/.ssh
    sudo chmod 700 /home/admin/.ssh && sudo chmod 600 /home/admin/.ssh/authorized_keys

    # Allow passwordless sudo for admin (safe: account is key-auth only)
    echo 'admin ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/admin-nopasswd
    sudo chmod 440 /etc/sudoers.d/admin-nopasswd

After this, always SSH as admin for privileged operations:

    ssh -o BatchMode=yes admin@100.79.225.3 "sudo <command>"

### SDDM Autologin (LXQt / Lubuntu)

For passwordless autologin on Lubuntu/LXQt with SDDM:

    sudo tee /etc/sddm.conf > /dev/null << 'EOF'
    [Autologin]
    User=galina
    Session=Lubuntu
    Relogin=false
    EOF

    # Remove password so Enter works at login screen if autologin is bypassed
    sudo passwd -d galina

Verify: `sudo passwd -S galina` shows `NP` (No Password).

## LXQt / PCManFM-Qt Desktop Configuration

All user settings live in `/home/galina/.config/`. Edit remotely with sudo as admin.

### Suppress execute/open confirmation dialog

File: `/home/galina/.config/pcmanfm-qt/lxqt/settings.conf`

    sudo sed -i 's/QuickExec=false/QuickExec=true/' /home/galina/.config/pcmanfm-qt/lxqt/settings.conf

With QuickExec=true, double-clicking a video file opens VLC immediately with no dialog.

### Remove desktop icons

Shortcuts are controlled by `DesktopShortcuts=` in settings.conf AND .desktop files in Desktop/.
Both must be updated:

    sudo rm /home/galina/Desktop/lubuntu-manual.desktop
    sudo rm /home/galina/Desktop/network.desktop
    sudo rm /home/galina/Desktop/firefox_firefox.desktop
    sudo sed -i 's/DesktopShortcuts=.*/DesktopShortcuts=Home, Trash, Computer/' \
      /home/galina/.config/pcmanfm-qt/lxqt/settings.conf

### Suppress all notifications

    # 1. Set do-not-disturb in notification daemon config
    sudo tee /home/galina/.config/lxqt/notifications.conf > /dev/null << 'EOF'
    [General]
    __userfile__=true
    doNotDisturb=true
    EOF

    # 2. Disable notification autostart entries by overriding with Hidden=true
    sudo mkdir -p /home/galina/.config/autostart
    for f in lxqt-notifications.desktop org.kde.discover.notifier.desktop; do
      sudo tee /home/galina/.config/autostart/$f > /dev/null << 'EOF'
    [Desktop Entry]
    Hidden=true
    EOF
    done
    sudo chown -R galina:galina /home/galina/.config/autostart

## LXQt Panel (Taskbar) Quicklaunch Shortcuts

Add application shortcuts to the LXQt panel quicklaunch plugin by editing panel.conf.
The quicklaunch plugin section must reference .desktop file paths directly.

### Find correct .desktop paths

    sudo find /usr/share/applications /var/lib/snapd/desktop/applications \
      -name 'chromium*.desktop' -o -name 'vlc.desktop' -o -name 'libreoffice-writer.desktop' 2>/dev/null

For Chromium snap: path is typically `/var/lib/snapd/desktop/applications/chromium_chromium.desktop`
For VLC: `/usr/share/applications/vlc.desktop`
For LibreOffice Writer: `/usr/share/applications/libreoffice-writer.desktop`

### Append quicklaunch section to panel.conf

    sudo tee -a /home/galina/.config/lxqt/panel.conf > /dev/null << 'EOF'

    [quicklaunch]
    alignment=Left
    apps\1\desktop=/var/lib/snapd/desktop/applications/chromium_chromium.desktop
    apps\2\desktop=/usr/share/applications/libreoffice-writer.desktop
    apps\3\desktop=/usr/share/applications/vlc.desktop
    EOF

### Panel reload pitfall — DO NOT use killall remotely

Killing lxqt-panel via SSH (`killall lxqt-panel` or `lxqt-panel --restart`) without a
proper session bus leaves the panel dead. It cannot be relaunched from SSH without the
DBUS_SESSION_BUS_ADDRESS — the process spawns but cannot connect to the session.

**The only safe remote panel reload is a full reboot:**

    sudo reboot

Panel changes take effect automatically when the session restarts. Do not attempt
`killall lxqt-panel && lxqt-panel &` via SSH — it looks like it works but the new
process dies silently or runs without plugins.

## Chromium Policy Configuration (Snap Build)

The Chromium snap reads policies from a non-standard path (NOT /etc/chromium/policies).
The correct path for the snap build is:

    /home/galina/snap/chromium/current/etc/chromium/policies/managed/

Create it and write JSON policy files:

    sudo mkdir -p /home/galina/snap/chromium/current/etc/chromium/policies/managed
    sudo tee /home/galina/snap/chromium/current/etc/chromium/policies/managed/galina.json > /dev/null << 'EOF'
    {
      "PromptForDownloadLocation": false,
      "DownloadDirectory": "/home/galina/Downloads",
      "RestoreOnStartup": 1,
      "ShowHomeButton": true,
      "HomepageLocation": "https://www.google.com",
      "HomepageIsNewTabPage": false,
      "PasswordManagerEnabled": false,
      "AutofillAddressEnabled": false
    }
    EOF
    sudo chown -R galina:galina /home/galina/snap/chromium/current/etc/chromium/policies

Note: `RestoreOnStartup: 1` = restore last session silently (no crash dialog, no prompt).
`InactiveTabTimeout` is a Chrome Enterprise-only policy — NOT available in Chromium snap.
For tab auto-close use the Tab Wrangler extension (ID: egnjhciaieeiiohknchakcodbpgjnchh).

### Force-install an extension via policy

Add to the JSON policy file:

    "ExtensionInstallForcelist": [
      "egnjhciaieeiiohknchakcodbpgjnchh;https://clients2.google.com/service/update2/crx"
    ]

Note: Tab Wrangler extension still requires manual configuration after first install
(set idle time to desired minutes — 2880 = 48 hours). The policy only installs it silently.

## Desktop Simplification for Non-Technical Users (LXQt)

### Disable right-click on desktop (prevent accidental layout changes)

    sudo tee -a /home/galina/.config/pcmanfm-qt/lxqt/settings.conf.d/lock.conf > /dev/null << 'EOF'
    [Desktop]
    EnableContextMenu=false
    EOF

### Disable screen lock and screensaver entirely

Via autostart entry that calls xset on session start:

    sudo tee /home/galina/.config/autostart/disable-screensaver.desktop > /dev/null << 'EOF'
    [Desktop Entry]
    Type=Application
    Name=Disable Screensaver
    Exec=xset s off -dpms
    Hidden=false
    NoDisplay=false
    X-GNOME-Autostart-enabled=true
    EOF
    sudo chown galina:galina /home/galina/.config/autostart/disable-screensaver.desktop

Also disable LXQt power management idle actions:

    sudo tee /home/galina/.config/lxqt/lxqt-powermanagement.conf > /dev/null << 'EOF'
    [General]
    __userfile__=true

    [Backlight]
    enableIdleAction=false

    [AC]
    enableIdleAction=false

    [Battery]
    enableIdleAction=false
    EOF
    sudo chown galina:galina /home/galina/.config/lxqt/lxqt-powermanagement.conf

### Set wallpaper via pcmanfm-qt config

    # Download a calm wallpaper (e.g. misty forest from Unsplash)
    sudo curl -sL 'https://images.unsplash.com/photo-1448375240586-882707db888b?w=1366&q=85' \
      -o /home/galina/Pictures/wallpaper.jpg
    sudo chown galina:galina /home/galina/Pictures/wallpaper.jpg

    # Set in pcmanfm config
    sudo sed -i 's|^Wallpaper=.*|Wallpaper=/home/galina/Pictures/wallpaper.jpg|' \
      /home/galina/.config/pcmanfm-qt/lxqt/settings.conf
    # If key doesn't exist, append it
    grep -q '^Wallpaper=' /home/galina/.config/pcmanfm-qt/lxqt/settings.conf || \
      echo 'Wallpaper=/home/galina/Pictures/wallpaper.jpg' | \
      sudo tee -a /home/galina/.config/pcmanfm-qt/lxqt/settings.conf

### Chromium Preferences via Python (session restore, no crash dialog)

Chromium must not be running when editing the Preferences file:

    sudo python3 << 'EOF'
    import json
    prefs_path = '/home/galina/snap/chromium/common/chromium/Default/Preferences'
    with open(prefs_path) as f:
        p = json.load(f)
    p.setdefault('session', {})['restore_on_startup'] = 1
    p.setdefault('profile', {})['exit_type'] = 'Normal'
    p.setdefault('profile', {})['exited_cleanly'] = True
    with open(prefs_path, 'w') as f:
        json.dump(p, f)
    print('done')
    EOF

## GRUB Boot Menu — Silent Boot Configuration

Target: boot straight to desktop with no menu visible. Hold Shift at boot to reveal menu.

### Why the menu shows despite GRUB_TIMEOUT=0

Two common root causes on Ubuntu/Lubuntu:

1. **Lubuntu GRUB theme override** — `/etc/default/grub.d/lubuntu-grub-theme.cfg` sets
   `GRUB_THEME=...` which forces the graphical menu to appear regardless of TIMEOUT_STYLE.
   Fix: `sudo rm /etc/default/grub.d/lubuntu-grub-theme.cfg && sudo update-grub`

2. **GRUB_RECORDFAIL_TIMEOUT unset** — If the last boot was flagged as a "recordfail" (e.g.
   after SSH reboot or hard power-off), GRUB ignores TIMEOUT_STYLE=hidden and shows the menu
   for 30 seconds (the hardcoded default). Fix: add to `/etc/default/grub`:
   `GRUB_RECORDFAIL_TIMEOUT=0`
   Then: `sudo update-grub`

3. **Multiple kernel entries** — Old kernels generate extra menu entries making the menu
   appear more prominently. Remove with:
   `dpkg -l | grep <old-kernel-version>` then `sudo apt purge linux-image-<version> ...`
   Also set: `GRUB_DISABLE_RECOVERY="true"` in `/etc/default/grub` to suppress recovery entries.

### Full silent-boot config

    # /etc/default/grub
    GRUB_DEFAULT=0
    GRUB_TIMEOUT_STYLE=hidden
    GRUB_TIMEOUT=0
    GRUB_RECORDFAIL_TIMEOUT=0          # prevents 30s fallback on recordfail
    GRUB_DISABLE_RECOVERY="true"       # no recovery mode entries
    GRUB_CMDLINE_LINUX_DEFAULT="quiet" # no splash = no plymouth overhead

    sudo update-grub

Verify the generated cfg: `sudo grep -E 'timeout|menuentry' /boot/grub/grub.cfg | head -10`
Look for `set timeout=0` (not 30) on the initial fallback line.

### Key-to-menu

GRUB only supports **Shift** or **Esc** to reveal the menu. F-keys are not interceptable
at GRUB stage — the BIOS may claim F12 before GRUB even loads (HP machines: F12 = boot
device selector). Shift is the reliable cross-platform choice.

---

## Advanced Boot Time Optimisation (Ubuntu with Snap)

After the basic optimisation in the section above, further gains come from auditing
`systemd-analyze critical-chain` to find what's actually blocking graphical.target.

### Additional services to mask/disable (Ubuntu 26.04 + snap)

| Service | Saving | Why safe to remove |
|---|---|---|
| grub-initrd-fallback.service | 32s | Safety net for bad boots; recordfail-triggered. Mask it: `sudo systemctl mask grub-initrd-fallback.service` |
| NetworkManager-wait-online.service | 7s | Blocks boot until full connectivity. Disable: `sudo systemctl disable NetworkManager-wait-online.service` |
| avahi-daemon.service + socket | 5s | mDNS/Bonjour — not needed on a media PC. Mask both. |
| switcheroo-control.service | 4s | Hybrid GPU switcher — irrelevant if no dGPU. Mask it. |
| cups.service + cups-browsed.service | 5s | Printing — mask if no printer needed. cups-browsed blocks critical chain. |
| gpu-manager.service | 4s | Detects hybrid GPU. Irrelevant on Sandy Bridge. Mask it. |
| thermald.service | 5s | Intel thermal daemon — earlyoom already handles pressure. Mask. |
| rsyslog.service | 4s | Systemd journal already handles logging. Disable. |
| smartmontools.service | 3s | Disk health daemon — not boot-critical. Disable. |
| ModemManager.service | 3s | 3G/4G modem manager — not needed on WiFi-only laptop. Mask. |
| sysstat.service | 3s | System activity reporting — not needed. Disable. |
| lm-sensors.service | 3s | Temperature monitoring daemon — disable if earlyoom installed. |
| accounts-daemon.service | 6s | User account manager — safe to mask with SDDM autologin. |
| udisks2.service | 6-21s | Disk management — mask if no USB drives needed at boot. |
| modprobe@efi_pstore.service | 4s | EFI panic log storage — not needed. Mask. |
| Plymouth services | 2-3s | Boot splash — remove by setting CMDLINE to `quiet` (no splash). |

Batch mask command:

    sudo systemctl mask \
      grub-initrd-fallback.service \
      avahi-daemon.service avahi-daemon.socket \
      switcheroo-control.service \
      cups.service cups.socket cups-browsed.service \
      gpu-manager.service \
      thermald.service \
      ModemManager.service \
      accounts-daemon.service \
      udisks2.service \
      modprobe@efi_pstore.service

    sudo systemctl disable \
      NetworkManager-wait-online.service \
      rsyslog.service \
      smartmontools.service \
      sysstat.service \
      lm-sensors.service

### Tailscale: don't block on NetworkManager-wait-online

By default, tailscaled waits for network-online.target (which waits for NM-wait-online).
Override to only need basic network.target:

    sudo mkdir -p /etc/systemd/system/tailscaled.service.d/
    sudo tee /etc/systemd/system/tailscaled.service.d/no-wait-online.conf > /dev/null << 'EOF'
    [Unit]
    After=network.target
    Wants=network.target
    EOF
    sudo systemctl daemon-reload

### Snap is the biggest remaining bottleneck

With Chromium snap: sys-module-fuse + loop devices + snapd = ~10-15s unavoidable at boot.
Eliminating snap entirely (replace Chromium snap with Firefox native deb) saves the most.
See Firefox Migration section below.

### Benchmarks (HP Pavilion G6 / Sandy Bridge / HDD)

| State | Total | Graphical target |
|---|---|---|
| Baseline (before any tuning) | 63s | 54s |
| After basic optimisation | 44s | 35s |
| After advanced service masking | 36s | 28s |
| After snap removal + Firefox deb | 33s | 22s |

---

## Firefox Native Deb Migration (replacing Chromium snap)

On Ubuntu 22.04+, both `firefox` and `chromium-browser` apt packages are snap redirect
stubs. The stub has an epoch (`1:1snap1`) that beats any direct version number, so naively
running `apt install firefox` installs the stub, not a real deb.

### Install Firefox from Mozilla's official apt repo

    # Add Mozilla's signing key
    sudo install -d -m 0755 /etc/apt/keyrings
    wget -q https://packages.mozilla.org/apt/repo-signing-key.gpg -O- | \
      sudo tee /etc/apt/keyrings/packages.mozilla.org.asc > /dev/null

    # Add the repo
    echo 'deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main' | \
      sudo tee /etc/apt/sources.list.d/mozilla.list > /dev/null

    # Pin Mozilla repo at priority 1000 to beat the snap stub's epoch
    sudo tee /etc/apt/preferences.d/mozilla << 'EOF'
    Package: *
    Pin: origin packages.mozilla.org
    Pin-Priority: 1000
    EOF

    # Remove snap stub FIRST, then install real deb
    sudo apt remove -y firefox
    sudo apt update -qq
    sudo apt install -y firefox

    firefox --version   # should show Mozilla Firefox 154.x

Pitfall: `apt install -y firefox` without removing the stub first will fail with
"Packages were downgraded and -y was used without --allow-downgrades" — the epoch
`1:1snap1` is numerically higher than `154.0`. Always remove stub first.

### Remove Chromium snap and purge snapd entirely

    # Remove snaps one at a time (snapd locks during each operation)
    sudo snap remove chromium
    sudo snap remove gnome-46-2404 gtk-common-themes mesa-2404 core22 core24 bare

    # Purge snapd completely
    sudo apt purge -y snapd
    sudo rm -rf /snap /var/snap /var/lib/snapd /var/cache/snapd /home/galina/snap

    # Update panel quicklaunch: replace snap path with Firefox deb path
    sudo sed -i 's|/var/lib/snapd/desktop/applications/chromium_chromium.desktop|/usr/share/applications/firefox.desktop|' \
      /home/galina/.config/lxqt/panel.conf

### Firefox enterprise policies

Policies go in `/etc/firefox/policies/policies.json` (not a snap path):

    sudo mkdir -p /etc/firefox/policies
    sudo tee /etc/firefox/policies/policies.json > /dev/null << 'EOF'
    {
      "policies": {
        "DisableTelemetry": true,
        "DisableFirefoxStudies": true,
        "DisablePocket": true,
        "OfferToSaveLogins": false,
        "PasswordManagerEnabled": false,
        "Homepage": {
          "URL": "https://www.google.com",
          "Locked": false,
          "StartPage": "homepage"
        },
        "DisplayBookmarksToolbar": "never",
        "NoDefaultBookmarks": true,
        "PromptForDownloadLocation": false,
        "DefaultDownloadDirectory": "/home/galina/Downloads",
        "DontCheckDefaultBrowser": true,
        "Extensions": {
          "Install": [
            "https://addons.mozilla.org/firefox/downloads/latest/tab-wrangler/latest.xpi"
          ]
        },
        "3rdparty": {
          "Extensions": {
            "tabwrangler@tabwrangler.com": {
              "minTabInactiveTime": 2880,
              "minTabs": 5
            }
          }
        }
      }
    }
    EOF

Tab Wrangler `minTabInactiveTime` is in minutes. 2880 = 48 hours.
Note: managed storage policy support depends on the extension's manifest — verify
Tab Wrangler respects it on first launch; if not, the user sets it manually once.

### Firefox user preferences (user.js)

Pre-seed a profile before first launch:

    PROFILE="/home/galina/.mozilla/firefox/galina.default"
    sudo mkdir -p "$PROFILE"
    sudo tee "$PROFILE/user.js" > /dev/null << 'EOF'
    user_pref("browser.startup.page", 3);                    // restore last session
    user_pref("browser.sessionstore.resume_from_crash", true);
    user_pref("browser.sessionstore.max_resumed_crashes", -1);
    user_pref("browser.sessionstore.restore_on_demand", false); // no crash prompt
    user_pref("browser.download.dir", "/home/galina/Downloads");
    user_pref("browser.download.folderList", 2);
    user_pref("browser.download.useDownloadDir", true);
    user_pref("signon.rememberSignons", false);
    user_pref("browser.shell.checkDefaultBrowser", false);
    user_pref("datareporting.healthreport.uploadEnabled", false);
    user_pref("browser.toolbars.bookmarks.visibility", "never");
    user_pref("browser.newtabpage.activity-stream.showSponsored", false);
    user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);
    EOF
    sudo chown -R galina:galina /home/galina/.mozilla

---

## LXQt Screen Blank Without Logout (TV-Friendly)

Target: screen off after 5 min idle, wakes on any mouse/keyboard input. No login prompt.

### Via xset autostart (reliable, works with any compositor)

    sudo tee /home/galina/.config/autostart/screen-blank.desktop > /dev/null << 'EOF'
    [Desktop Entry]
    Type=Application
    Name=Screen Blank After 5min
    Exec=sh -c 'xset s 300 300 && xset dpms 0 0 0 && xset +dpms'
    Hidden=false
    NoDisplay=false
    X-LXDE-Autostart-Phase=Application
    EOF
    sudo chown galina:galina /home/galina/.config/autostart/screen-blank.desktop

`xset s 300 300` — blank after 300s idle  
`xset dpms 0 0 0` — disable standby/suspend/off timers (screen wakes on any input)  
`xset +dpms` — enable DPMS so xset s works  

### Via lxqt-powermanagement (complementary)

In `/home/galina/.config/lxqt/lxqt-powermanagement.conf`:

    enableIdlenessWatcher=true
    enableIdlenessBacklightWatcher=true
    idlenessACAction=0          # 0 = blank screen (not suspend/lock)
    idlenessBatteryAction=0

Note: the idlenessTime QVariant binary encoding is fragile via sed — use xset autostart
as the primary method and lxqt-powermanagement as a complement.

---

## LXQt Shutdown Without Confirmation Dialog

LXQt's logout/shutdown dialog shows a secondary "you may lose work" warning by default.
Disable via:

    sudo sed -i 's/leave_confirmation=true/leave_confirmation=false/' \
      /etc/xdg/xdg-Lubuntu/lxqt/session.conf

    # Also patch user's local copy if it exists
    sudo sed -i 's/leave_confirmation=true/leave_confirmation=false/' \
      /home/galina/.config/lxqt/session.conf 2>/dev/null || true

This key lives in the system-wide xdg config, not the user config — patch both.

---

## Automated Cleanup with Anacron


For periodic cleanup on a laptop that may be off when cron fires:
- Use `/etc/cron.daily/` not `/etc/cron.d/` — anacron monitors cron.daily and replays
  missed jobs on next boot (5-minute delay after startup).
- anacron is pre-installed on Ubuntu desktop. `/etc/cron.d/` jobs missed while off are lost.

    sudo tee /etc/cron.daily/galina-cleanup > /dev/null << 'EOF'
    #!/bin/bash
    find /home/galina/Downloads -type f -mtime +30 -delete
    find /home/galina/Videos -type f -mtime +30 -delete
    find /home/galina/Downloads -type d -empty -not -path '/home/galina/Downloads' -delete
    find /home/galina/Videos -type d -empty -not -path '/home/galina/Videos' -delete
    EOF
    sudo chmod 755 /etc/cron.daily/galina-cleanup
