---
name: tailscale-linux-setup
category: devops
description: Use when setting up or operating Tailscale VPN on Linux.
tags: [tailscale, vpn, mesh-vpn, networking, fedora, silverblue, ssh, tailnet]
related_skills: [protonvpn-nm-automation, linux-wifi-stability]
---

# Tailscale Linux Setup

Use when setting up Tailscale mesh VPN on Linux, connecting devices to a tailnet, or performing common operations (SSH between nodes, status check, auth, exit nodes). Validated on Fedora Silverblue (Atomic).

## Install

On Fedora Silverblue/Atomic — install into the layered base image:

    rpm-ostree install tailscale
    systemctl reboot

On standard Fedora/RHEL:

    dnf install tailscale

## Enable and Start

After reboot (or on any system where the package is installed but service not running):

    sudo systemctl enable --now tailscaled

Verify it's active:

    systemctl status tailscaled

## Authenticate

    sudo tailscale up

This prints a URL. Open it in a browser, log in to the Tailscale account, and authorize the device. The command will block — it times out after ~180s but the URL remains valid. Re-run `tailscale up` if it times out before you finish in the browser.

## Verify Connection

    tailscale status

Shows all devices in the tailnet with their Tailscale IPs (100.x.x.x range) and hostnames.

## SSH Between Tailnet Nodes

Use the Tailscale IP or MagicDNS hostname:

    ssh username@100.x.x.x
    # or if MagicDNS is enabled:
    ssh username@hostname

### First-connect host key issue

If you get "Host key verification failed" on first SSH, the host key isn't trusted yet. Accept it with:

    ssh -o StrictHostKeyChecking=accept-new username@100.x.x.x

Do NOT run SSH through the agent's terminal tool (non-interactive). For actual interactive SSH, the user must run it in their own terminal. The agent can verify connectivity via `tailscale ping <host>` and check status, but cannot open an interactive session.

### Passwordless SSH setup

After first connect, set up key auth:

    ssh-copy-id username@100.x.x.x

## Useful Commands

    tailscale ping <hostname>            # test reachability
    tailscale status --json              # machine-readable status
    tailscale ip                         # this machine's Tailscale IP
    tailscale logout                     # deauth this device
    tailscale up --advertise-exit-node   # make this machine an exit node
    tailscale up --exit-node=<ip>        # route traffic through an exit node
    tailscale up --ssh                   # enable Tailscale SSH (key-managed)

## Checking for Updates

    tailscale version                    # show current version
    sudo tailscale update --dry-run      # check if update is available without applying
    sudo tailscale update                # apply update

Note: `tailscale update --check` does NOT exist — the flag is `--dry-run`.

## Pitfalls

- On Fedora with firewalld, the `tailscale0` interface gets NO zone by default — SSH over Tailscale is silently blocked even after you open port 22. Always assign the interface to the trusted zone: `sudo firewall-cmd --permanent --zone=trusted --add-interface=tailscale0 && sudo firewall-cmd --reload`. Verify with `sudo firewall-cmd --get-zone-of-interface=tailscale0`.
- If SSH is "connection refused" over Tailscale despite sshd running and port 22 open in the public zone, the first thing to check is the zone assignment of `tailscale0` — it will show "no zone" until manually assigned.
- On Fedora Silverblue, sshd is installed but disabled and inactive by default — always check `systemctl status sshd` first; enable with `sudo systemctl enable --now sshd`.
- `tailscale up` blocks and times out after ~180s — the auth URL stays valid; just re-run if it expires before browser auth completes.
- SSH via agent terminal will fail with "Pseudo-terminal will not be allocated" — expected; the user must run interactive SSH in their own terminal.
- "Host key verification failed" on first connect is normal — use `StrictHostKeyChecking=accept-new` once.
- MagicDNS hostnames can be very long (e.g. `galina-hppaviliong6notebookpc`) — use Tailscale IPs in scripts, hostnames for human use.
- On Fedora Atomic, install via `rpm-ostree install tailscale` (not dnf), then reboot before enabling the service.
- `sudo snap remove <pkg>` locks snapd for the duration — never run two snap removes in the same command or parallel. Run sequentially: wait for first to finish (process wait or sleep 15) before issuing the next.
- Large remote commands (snap installs, apt with many packages) time out at default 180s — use `terminal(background=True, notify=True)` + `process(action='wait', timeout=300)` for anything that could take 2-5 minutes.

## Running Agent Commands on Remote Tailnet Nodes

Once key-based SSH auth is set up, the agent can run non-interactive commands on remote nodes directly via terminal():

    ssh -o BatchMode=yes galina@100.79.225.3 "<command>"

`BatchMode=yes` prevents SSH from hanging on password prompts — it will fail immediately if key auth is unavailable rather than blocking forever.

Useful remote management patterns:

    # Check OS
    ssh -o BatchMode=yes galina@100.79.225.3 "cat /etc/os-release"

    # Check for apt updates
    ssh -o BatchMode=yes galina@100.79.225.3 "sudo apt update -q 2>&1 && apt list --upgradable 2>/dev/null"

    # Apply updates silently
    ssh -o BatchMode=yes galina@100.79.225.3 "sudo apt upgrade -y 2>&1"

    # Install a package
    ssh -o BatchMode=yes galina@100.79.225.3 "sudo apt install -y <package> 2>&1"

Timeout note: snap installs (e.g. chromium) take 3-5 minutes; set terminal timeout=600 or run in background. The snap downloads core22 + the app itself — normal, just slow.

Phased updates on Ubuntu: `apt upgrade` may report "Not upgrading yet due to phasing" — this is Ubuntu's staged rollout mechanism, not an error. Packages will auto-apply once the machine's phase slot opens.

## Remote Ubuntu Management — Extended Patterns

See `references/ubuntu-hdmi-vlc-setup.md` for:
- Intel iGPU (Sandy Bridge) HDMI driver verification steps
- VA-API codec check via `vainfo`
- VLC vlcrc configuration for TV playback (hardware decode, fullscreen, cursor hide)
- Unattended-upgrades setup and auto-reboot config
- HDMI audio switch gotcha (must be done manually after plug-in)
- Large remote apt installs: use `background=True, notify=True` + `DEBIAN_FRONTEND=noninteractive`
- Hardware diagnostics: smartctl, lm-sensors, dmesg analysis for old laptops
- HP Pavilion G6 known issues: hp-wmi fan error (cosmetic, safe to ignore), BIOS update not worth doing
- Performance optimisation: zram-config, earlyoom, TLP, BFQ scheduler, swappiness tuning
- Boot time optimisation: systemd-analyze blame, disabling apport/grub2-common/networkd-dispatcher/snap bloat
- Snap removal pitfall: operations lock snapd — run sequentially not in parallel
- Fedora Silverblue (this machine) optimisation profile: almost nothing needed beyond swappiness + mask fwupd
- LXQt panel quicklaunch shortcuts + panel reload pitfall (reboot only — never killall via SSH)
- Chromium snap policy path (~/snap/chromium/current/etc/chromium/policies/managed/)
- Chromium Preferences JSON editing via Python (session restore, crash dialog suppression)
- InactiveTabTimeout not in Chromium snap — use Tab Wrangler extension force-install instead
- Desktop simplification for non-technical users: screensaver/lock disable, wallpaper, right-click lock, cleaned desktop
- Automated cleanup via anacron (cron.daily catches missed jobs on next boot)
- GRUB silent boot: Lubuntu theme override + GRUB_RECORDFAIL_TIMEOUT=0 + GRUB_DISABLE_RECOVERY — three root causes for menu appearing despite TIMEOUT=0
- Advanced boot service masking: 15+ services to mask/disable on Ubuntu 26.04 (cups, avahi, gpu-manager, accounts-daemon, udisks2, etc.) with benchmarks
- Firefox native deb migration: Mozilla PPA setup, snap stub epoch pitfall, snapd purge, enterprise policies, user.js pre-seed, Tab Wrangler 48h config
- LXQt screen blank without logout: xset autostart method (reliable) + lxqt-powermanagement complement
- LXQt shutdown confirmation: leave_confirmation=false in /etc/xdg/xdg-Lubuntu/lxqt/session.conf

## This User's Tailnet (as of 2026-09)

- `fedora` — 100.71.111.0 (this machine, amoni094@)
- `galina-hppaviliong6notebookpc` — 100.79.225.3 (amoni094@, SSH user: galina, OS: Ubuntu 26.04 LTS)
- `desktop-ph4f2dk` — 100.88.247.70 (Windows 11, SSH user: admin, pass in memory, installed 2026-09-02)
- `booran` — 100.115.122.121 (Windows 11 build 22631, grandparents' LAN 192.168.1.109, admin user: admin/Gunn1967, Leon user: Leon/pass; installed 2026-09-02 via scheduled task method through Galina jump host)
- `pixel-8a` — 100.95.234.52 (Android, amoni094@; SSH via Termux on port 8022)

Note: desktop-ph4f2dk is behind a Launtel NBN connection that previously had CGNAT. As of 2026-09-03 a static public IP (203.12.11.199) was assigned — CGNAT no longer applies to this address. External connections to the home router now work without Tailscale relay if the router's port forward is configured. WoL over the public internet is now viable via UDP/9 forward to 192.168.0.181.

## SSH into Android (Google Pixel) via Tailscale

Tailscale on Android provides network connectivity only — it does NOT run an SSH server. To SSH into a Pixel over Tailscale:

1. Install F-Droid on the phone (the Play Store Termux is outdated/crippled):
   - Open Chrome on the phone, go to f-droid.org
   - Download and install the F-Droid APK
   - When prompted, allow Chrome to install unknown apps
   - Let F-Droid update its package index after first launch

2. Install Termux from F-Droid (search "Termux", install the one by Fredrik Fornwall)

3. In Termux, set up sshd:

       pkg update && pkg install openssh
       passwd          # set a password for the Termux user
       sshd            # starts on port 8022 (not 22)

4. Connect from host:

       ssh -p 8022 100.95.234.52

Pitfalls:
- Termux sshd uses port 8022, not 22 — always pass `-p 8022`
- sshd must be started manually each time Termux is opened (or add `sshd` to `~/.bashrc` in Termux)
- F-Droid, not Play Store — Play Store Termux is abandonware and won't install modern packages
- If the phone screen locks, the SSH session stays alive but new connections may be refused depending on Android battery optimisation — disable battery optimisation for Termux in Android Settings

## Discovering a New Device on the LAN via Galina (Jump Host)

Before targeting a new Windows machine remotely, confirm its IP and that SSH is reachable. Run these from your local machine via Galina as jump host:

    # Ping sweep to find live hosts — scan FULL /24, not just a sub-range; new devices can land anywhere
    ssh -o BatchMode=yes galina@100.79.225.3 \
      "for i in \$(seq 1 254); do (ping -c1 -W1 192.168.1.\$i &>/dev/null && echo \"192.168.1.\$i UP\") & done; wait"

    # Check ARP table for recently-seen MACs
    ssh -o BatchMode=yes galina@100.79.225.3 "ip neigh show"

    # Port scan candidates for SSH (22), RDP (3389), WinRM (5985)
    ssh -o BatchMode=yes galina@100.79.225.3 \
      "for ip in 192.168.1.101 192.168.1.105 192.168.1.106; do \
         for port in 22 3389 5985; do \
           (timeout 2 bash -c \"echo >/dev/tcp/\$ip/\$port\" 2>/dev/null && echo \"\$ip:\$port OPEN\"); \
         done; done"

If port 22 is closed on all candidates, the issue is one of:
- Machine not yet connected to WiFi / not powered on
- OpenSSH Server installed but service not started (Windows Optional Features install ≠ service running)
- Windows Firewall blocking port 22 even with OpenSSH installed

**Windows OpenSSH pre-flight checklist (requires physical/RDP access once):**

    # In admin PowerShell — verify service is actually running:
    Get-Service sshd

    # If stopped:
    Start-Service sshd
    Set-Service sshd -StartupType Automatic

    # Open firewall if missing:
    netsh advfirewall firewall add rule name="OpenSSH" dir=in action=allow protocol=TCP localport=22

**sshpass dependency on Galina's laptop:** Password-based SSH jumps through Galina require `sshpass`. Install it once if missing:

    ssh -o BatchMode=yes galina@100.79.225.3 "sudo apt-get install -y sshpass"

## Installing Tailscale on Windows via SSH (no physical access)

If the machine only has SSH access (OpenSSH Server enabled but no GUI access), the standard installer and MSI both fail:
- `tailscale-setup.exe /quiet` — requires interactive window station (fails over SSH)
- `msiexec /i tailscale.msi /quiet` — requires Windows Installer Service access (fails: "service could not be accessed" over non-elevated SSH)

**Working method: Scheduled task as SYSTEM**

1. Download the installer — use `C:\Windows\Temp\` not `C:\Users\admin\Downloads\` (Downloads folder may not exist for admin account):
```
sshpass -p 'PASS' ssh admin@<IP> "powershell -NonInteractive -Command \"Invoke-WebRequest -Uri 'https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe' -OutFile 'C:\\Windows\\Temp\\tailscale-setup.exe'\""
```

2. Create and immediately run a SYSTEM scheduled task:
```
sshpass -p 'PASS' ssh admin@<IP> "schtasks /create /tn TailscaleInstall /tr \"cmd /c C:\\Windows\\Temp\\tailscale-setup.exe /quiet /norestart\" /sc once /st 00:00 /ru SYSTEM /rl HIGHEST /f && schtasks /run /tn TailscaleInstall && echo done"
```
The `/st 00:00` triggers a "past time" warning but the task still creates and runs. Include `/rl HIGHEST` to ensure elevated privileges.

3. Wait ~20-30 seconds, then verify:
```
sshpass -p 'PASS' ssh admin@<IP> "schtasks /query /tn TailscaleInstall /fo LIST 2>&1 | findstr Status"
```
Expect `Status: Running` then `Status: Ready` (completed). Also check:
```
sshpass -p 'PASS' ssh admin@<IP> "sc query tailscale 2>&1 | findstr STATE"
```
Expect `STATE: 4 RUNNING`.

4. Authenticate — run `tailscale up` via the terminal and capture the URL. It blocks waiting for browser auth and times out after ~180s, but the URL stays valid:
```
sshpass -p 'PASS' ssh admin@<IP> "\"C:\\Program Files\\Tailscale\\tailscale.exe\" up" 2>&1
```
This prints `To authenticate, visit: https://login.tailscale.com/a/<token>` — open it in the browser and approve.

Alternatively, run it as a SYSTEM task (cleaner for background execution) and check the task's stdout:
```
# Run as SYSTEM task with output redirected to a temp file
sshpass -p 'PASS' ssh admin@<IP> 'schtasks /create /tn TailscaleUp /tr "cmd /c \"C:\\Program Files\\Tailscale\\tailscale.exe\" up > C:\\Windows\\Temp\\tsup.txt 2>&1" /sc once /st 00:00 /ru SYSTEM /f && schtasks /run /tn TailscaleUp'
sleep 8
sshpass -p 'PASS' ssh admin@<IP> 'type C:\Windows\Temp\tsup.txt'
```

5. Verify from your local machine (tunnel activates automatically on fresh installs — no tray click needed):
```
tailscale ping 100.x.x.x
```
Expect `pong from <hostname> via <relay> in <ms>`. Will be via relay initially; direct path establishes over minutes.

6. Clean up temp tasks and installer:
```
sshpass -p 'PASS' ssh admin@<IP> "schtasks /delete /tn TailscaleInstall /f & del C:\\Windows\\Temp\\tailscale-setup.exe"
```

**Key constraints for Windows install via SSH:**
- Must use the `admin` (local admin) account — standard users cannot create SYSTEM tasks or install services
- Use `C:\Windows\Temp\` for all temp files — `C:\Users\admin\Downloads\` may not exist
- Use `schtasks.exe` for task registration, NOT `New-ScheduledTaskSettingsSet` PowerShell cmdlet — PS5 booleans (`$false`) passed as positional args cause parse errors
- `tailscale status` hangs over SSH after install — use `sc query tailscale | findstr STATE` to check service state
- `tailscale up --authkey=<key>` is cleaner than browser auth if you have a reusable auth key from the Tailscale admin console
- Tailscale auto-starts with Windows after install and auth — no further config needed

## Windows Remote Maintenance Deployment

To deploy recurring maintenance scripts to a Windows node via SSH, see `references/windows-maintenance-deployment.md`.
The pattern: upload PS1 to `C:\Windows\System32\`, register via `schtasks /create /ru SYSTEM /rl HIGHEST`, verify with `schtasks /query /tn <name> /fo LIST`.

Also covered in that reference:
- Auto-delete Downloads folder on a schedule (30-day policy)
- Windows autologin for a standard user account (Winlogon registry keys)
- Windows security hardening for non-technical users: Cloudflare 1.1.1.2 DNS (malware+phishing, NOT adult content), Defender PUA/NetworkProtection/CloudBlockLevel, SmartScreen policy enforcement via Edge registry
- Staged deploy pattern: push a self-deleting cron to jump host for when target is temporarily offline
