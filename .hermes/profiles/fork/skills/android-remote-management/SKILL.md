---
name: android-remote-management
description: Use when managing Android phone remotely via SSH/ADB.
---

# Android Remote Management

## Connection — Pixel 8a via Tailscale SSH

The confirmed working path:

    ssh -p 8022 -o IdentitiesOnly=yes -i ~/.ssh/pixel_termux <tailscale-ip> "<command>"

Key details:
- Tailscale node: pixel-8a-1, IP 100.109.174.100 (use this — pixel-8a at 100.95.234.52 is stale/offline)
- SSH key: ~/.ssh/pixel_termux
- Default PATH in the SSH session does NOT include Android system binaries. Prepend manually:

    export PATH=/system/bin:/system/xbin:$PATH

- Multiple keys in ssh-agent trigger "Too many authentication failures" — always pass -o IdentitiesOnly=yes.

## Prerequisites — phone side before connecting

1. Tailscale app shows Connected (green toggle)
2. RethinkDNS has Tailscale set to "Bypass universal" (Configure > Apps) — RethinkDNS WireGuard intercepts Tailscale traffic and drops it otherwise
3. RethinkDNS has Termux set to "Bypass universal" — otherwise Termux sshd port is blocked by the VPN
4. Termux sshd is running (restart it in the app if SSH times out after Tailscale reconnects)

## WiFi 'Connected, no internet' on home network

When phone shows connected but no internet on a previously-working network, RethinkDNS is first suspect (classic chicken-and-egg: WiFi broken → Tailscale down → phone unreachable remotely, so diagnose via router/Pi from host or guide user manually).

Pitfall: Before chasing the phone, check the host's LAN reachability. ProtonVPN (proton0 interface) tunnels all traffic including LAN-destined packets — `ping 192.168.0.1` and `ping 192.168.0.138` will return "Destination Host Unreachable" even if the LAN is healthy. Confirm with `ip addr show proton0`; if it's UP and LAN pings fail, the phone and Pi may be fine. Use `tailscale status` and SSH to the Pi via LAN IP to verify independently.

Pitfall: If the Pi runs Technitium DNS (`dns.service`) and it reboots or the service stops, every device using the Pi as DNS resolver — including the phone — shows "connected, no internet" even though the network is up. Check `ssh rainbowpi@192.168.0.138 "uptime && systemctl is-active dns.service"` before suspecting the phone. Service name is `dns`, not `technitium-dns`.

Fix sequence once Pi DNS is confirmed healthy:
1. Pause RethinkDNS (notification shade key icon) — if internet returns immediately, RethinkDNS is the remaining cause.
2. Check RethinkDNS DNS upstream: Configure → DNS → verify Cloudflare DoT (tls://1.1.1.1) responding; try tls://8.8.8.8 to confirm.
3. If not RethinkDNS: forget network → reconnect (home pw: Gunn1967).
4. Last resort: Airplane mode 10s then off to force DHCP renew.

## What Termux SSH can do (uid 10460, no root)

- Run Termux-scoped commands and scripts
- Launch Android intents via `am start` for exported activities only
- Access Termux's own file space
- Run /system/bin binaries that don't require a privileged uid

## Hard wall: Android 14 blocks Termux SSH from system settings

Termux uid 10460 cannot:
- `settings get/put system|global|secure` — SecurityException: INTERACT_ACROSS_USERS required
- `dumpsys notification` — permission denied
- `cmd notification get-channels <pkg>` — permission denied
- Read /data/data/<other-app>/shared_prefs/ — SELinux denies cross-app data
- Write notification channel state for other apps

This wall cannot be bypassed without root or ADB shell. ADB shell runs as uid `shell` which holds INTERACT_ACROSS_USERS.

## ADB over network (requires prior on-phone setup)

If Wireless debugging is enabled (Developer Options > Wireless debugging):

    # Install adb if missing
    sudo dnf install android-tools

    adb connect <tailscale-ip>:5555
    adb shell settings get system ringer_mode
    adb shell settings put system vibrate_when_ringing 1
    adb shell settings put system haptic_feedback_enabled 1
    adb shell settings put system notification_vibration_intensity 7
    adb shell cmd notification get-channels com.whatsapp

Pitfall: Wireless debugging resets on reboot and cannot be re-enabled remotely via Termux SSH without root. Enable it before closing the phone session if it will be needed again.

Pitfall: adb is not installed on the Fedora host by default — run `sudo dnf install android-tools` first.

## Notification vibration — manual fix (when remote path is blocked)

When ADB and root are unavailable, these are the exact on-phone paths:

**System level (check first — its slider overrides per-app settings):**
Settings > Sound & vibration > Vibration intensity > Notifications slider must not be at zero

**DND (silently kills all vibration):**
Settings > Sound & vibration > Do Not Disturb — off, or add Messages/WhatsApp to allowed apps

**Google Messages:**
Open app > profile icon (top right) > Messages settings > Notifications > Default > Vibrate > On

**WhatsApp (independent in-app toggle that overrides system setting):**
WhatsApp > Settings > Notifications > Message notifications > Vibrate > Short or Long
("None" kills vibration even when system vibration is on)
