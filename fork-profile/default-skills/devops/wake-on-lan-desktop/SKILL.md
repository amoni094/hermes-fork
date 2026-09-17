---
name: wake-on-lan-desktop
description: Use when remotely booting the desktop via WoL.
tags: [wol, desktop, remote-boot, network]
related_skills:
  - windows-remote-admin
  - tailscale-linux-setup
  - linux-wifi-stability
---

# Wake Desktop Remotely

## IMPORTANT: Wi-Fi only — use Sleep (S3), not Shutdown
ASRock Z390 + Intel AX200 does NOT support WoL from cold shutdown over Wi-Fi.
Always Sleep the desktop (not shut down) to enable remote wake.

## One-liner (from anywhere — works when desktop is in S3 Sleep)
```bash
python3 -c "import wakeonlan; wakeonlan.wake('70:D8:C2:70:0D:B4', ip='144mckinnon.servecounterstrike.com', port=9)"
```

## Network details
- Desktop: DESKTOP-PH4F2DK
- Wi-Fi adapter (Intel AX200): MAC 70:D8:C2:70:0D:B4  <-- use this for WoL
- Ethernet adapter (Intel I219-V): MAC 70:85:C2:C0:6D:3B  <-- NOT connected
- Desktop LAN IP: 192.168.0.181 (DHCP-reserved on AX55)
- DDNS: 144mckinnon.servecounterstrike.com (NO-IP, amoni094@gmail.com)
- Router port forward: UDP 9 -> 192.168.0.181:9 (enabled)
- Install: pip3 install wakeonlan

## Windows WoL settings (already configured 2026-09-03)
- Wi-Fi adapter PnPCapabilities = 0 (allow wake) — set via registry
- Wi-Fi *WakeOnMagicPacket = 1, *WakeOnPattern = 1 — confirmed enabled
- Ethernet PnPCapabilities = 0 (allow wake) — set via registry
- Ethernet Ultra Low Power Mode = Disabled — set via NIC properties
- Fast Startup = Disabled (HiberbootEnabled=0) — confirmed
- S3 (Standby) sleep = Available and supported

## Motherboard
- ASRock Z390 Extreme4
- BIOS: Power Management > Wake on LAN must be Enabled (manual BIOS check required)

## Workflow
1. Put desktop to Sleep (Start > Power > Sleep), NOT Shutdown
2. Wait ~10s for sleep to settle
3. Run the magic packet one-liner above from laptop
4. Desktop wakes in ~5-15s

## If you want cold-boot WoL
Option A: Plug in Ethernet cable — wired WoL from shutdown works on I219-V
Option B: Smart power plug (Kasa) — cut/restore mains, BIOS power-on-after-AC-loss

## Notes
- DDNS auto-updates via router when public IP changes
- If wake fails: verify desktop is in Sleep (not shutdown) + check BIOS WoL setting
