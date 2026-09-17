---
name: miracast-linux-silverblue
description: Use when casting screen to smart TV via Miracast on Linux.
tags: [miracast, fluxcast, wifi-direct, silverblue, lg-tv, screen-mirroring]
related_skills:
  - linux-wifi-stability
  - wayland-session-management
  - fedora-atomic-dotfiles-adaptation
---

# Miracast / Wi-Fi Direct Screen Casting on Fedora Silverblue

## Hardware prerequisite
Check P2P support: `iw phy phy0 info | grep -A2 "valid interface combinations"`
Need: `P2P-client, P2P-GO` in the combinations list.
Confirmed working: Intel AX201 (ThinkPad X1 Carbon Gen 9), AX200.

## Tool: FluxCast
FluxCast v0.2.3+ is the only working Miracast source on wlroots (Hyprland/Sway).
Uses: NetworkManager Wi-Fi Direct + RTSP/RTP + wf-recorder capture.
Latency: ~1 second at 720p30.

### Install
```bash
mkdir -p ~/.local/bin
# Download FluxCast.AppImage to ~/.local/bin/
cat > ~/.local/bin/fluxcast << 'EOF'
#!/usr/bin/env bash
APPIMAGE_EXTRACT_AND_RUN=1 /var/home/rainbow/.local/bin/FluxCast.AppImage "$@"
EOF
chmod +x ~/.local/bin/fluxcast
```

### One-time DBus policy setup (Silverblue — /usr is read-only)
FluxCast's setup script writes to `/usr/share/dbus-1/system.d/` which is read-only on Silverblue.
Extract AppImage and install policy to `/etc/dbus-1/system.d/` instead:
```bash
cd /tmp
APPIMAGE_EXTRACT_AND_RUN=1 ~/.local/bin/FluxCast.AppImage --appimage-extract
sudo install -Dm644 /tmp/squashfs-root/meta/zz-dev.fluxcast.wpa-supplicant.conf \
  /etc/dbus-1/system.d/zz-dev.fluxcast.wpa-supplicant.conf
sudo systemctl reload dbus
```
FluxCast still prints a warning about /usr/share on each run — cosmetic, harmless.

## ProtonVPN conflict
Miracast P2P conflicts with ProtonVPN killswitch.
Wrapper `~/.local/bin/fluxcast-cast` handles VPN teardown and restore automatically.

## TV requirements

### LG webOS (home TV at 192.168.0.107)
- Enable Screen Share: Home > Settings > Connection > Screen Share > ON
- Verify reachable: `bash -c "echo '' > /dev/tcp/192.168.0.107/3000" && echo open`
- TV must show "Waiting for connection..." before casting

### Samsung / Panasonic
- Put TV into Screen Share / Miracast mode manually before casting

## Cast command
```bash
fluxcast-cast --protocol wfd --output-res 1280x720 --fps 30 --bitrate 3M
```
Scans for P2P beacons and connects automatically once TV is in Screen Share mode.

## Pitfalls
- Do NOT use MiracleCast: Display-Source unimplemented, requires stopping NetworkManager, not in Fedora repos.
- AppImage requires `APPIMAGE_EXTRACT_AND_RUN=1` on Silverblue (no libfuse.so.2).
- DBus policy silently fails to /usr/share on Silverblue — always install to /etc/dbus-1/system.d/ instead.
- wf-recorder must be installed: `which wf-recorder`.
- LG webOS cannot send UDP/WoL packets via its API — pairing does not enable WoL relay.
- Panasonic VIERA has no AirPlay (port 7000 closed), no SSH; Screen Share mode is manual-only.

## Adoption note for related user-owned skills
Run `hermes curator adopt wake-on-lan-desktop` and `hermes curator adopt tplink-ax55-router-automation`
to enable future autonomous updates. Key facts to patch once adopted:

wake-on-lan-desktop:
- Port changed UDP/9 -> UDP/47293 (external) -> 192.168.0.181:9 (internal), 2026-09-03
- Hybrid sleep (S4) silently blocks WoL; HYBRIDSLEEP alias fails on built-in plans, use raw GUIDs
  Subgroup GUID: 238c9fa8-0aad-41ed-83f4-97be242c8f20, Setting GUID: 94ac6d29-73ce-41a6-809f-6363ba21b47e
- AX200 Wi-Fi NIC loses power during S3 sleep; wired Ethernet (I219-V) needed for reliable WoL
- SSH sleep command: powershell SetSuspendState; SSH timeout = sleep fired (expected)
- Run `powercfg /hibernate off` for pure S3

tplink-ax55-router-automation:
- Port forwarding page route: `#/portForwarding`
- Advanced menu is at approx coordinate (979, 107) on 1280x800 viewport
- Edit icon for first rule row: (1033, 412); delete: (1058, 412)
- External Port field: x~640, y~472; clear with Ctrl+A then type
- Save button on port forwarding page: `page.locator('button:has-text("SAVE")').last.click()` works
- `text=Advanced` locator fails (element not visible); use coordinate click instead
