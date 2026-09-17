# DESKTOP-PH4F2DK Stable Configuration (as of Sep 3 2026)

## Hardware
- CPU: Intel i7-9700K (Coffee Lake, 8C/8T)
- Motherboard: ASRock Z390 Extreme4, BIOS P4.30F (Sep 2022)
- GPU: NVIDIA RTX 2080 (215W TDP), driver 595.97
- RAM: 16GB Kingston DDR4-2400 (2x8GB, dual-channel A1/B1 slots)
- NIC: Intel AX200 Wi-Fi (primary), Intel I219-V Ethernet (unused)
- OS: Windows 11 Pro Build 26200

## BIOS Settings (OC Tweaker)
- CPU All-Core Ratio: 49 (4.9 GHz)
- CPU Core Voltage: 1.30V fixed
- Long Duration Power Limit (PL1): 250W
- Short Duration Power Limit (PL2): 250W
- C6/C7 State: Disabled
- XMP Profile: 1 (DDR4-2400)
- CPU ratio 50 (5.0 GHz) was tested and UNSTABLE at both 1.30V and 1.32V with XMP on

## GPU (RTX 2080)
- Power limit: 240W (set by NvidiaMaxPowerLimit2 scheduled task on SYSTEM startup)
- MSI Afterburner: installed at C:\Program Files (x86)\MSI Afterburner\
  - Start with Windows: DISABLED (causes login crash if enabled with CPU OC)
  - OC profile: Core +50, Memory +500, Temp limit 83C
  - Apply manually after boot if desired
- NVIDIA Control Panel: Low Latency Mode=Ultra, Power Management=Prefer Maximum Performance
- HAGS: Enabled (HwSchMode=0x2)

## Windows Optimizations Applied (Sep 2-3 2026)
- Power plan: Ultimate Performance
- Sleep/Fast Startup: Disabled
- Game DVR: Disabled
- TDR delay: 8 seconds
- MMCSS Games priority: 6
- SystemResponsiveness: 0
- GlobalTimerResolutionRequests: 1
- HAGS: Enabled
- Game Mode: Enabled
- SysMain: Enabled
- Pagefile: 2048-4096 MB (manual, not system-managed)
- Telemetry/Xbox/Edge startup boost services: Disabled
- I219-V NIC: MSI enabled, IRQ pinned core 7, RSS 4 queues, interrupt moderation off
- AX200 Wi-Fi: 5GHz preferred, MIMO power save off, roaming aggressiveness lowest

## SSH/Remote Access
- SSH server: OpenSSH (Windows built-in), listening port 22
- Tailscale IP: 100.88.247.70
- LAN IP: 192.168.0.181
- Admin account: admin (password in user memory)
- Active console user: rainbow

## Scheduled Tasks
- NvidiaMaxPowerLimit2: `nvidia-smi.exe -pl 240` at SYSTEM startup
- LeonMaintenance: Sunday 3AM, C:\Windows\System32\leon-maintenance.ps1

## Known Issues / Constraints
- USB Legacy Support: disabled in BIOS. Keyboard/mouse don't work at BIOS POST.
  User must use a USB device that works without legacy support, or accept BIOS is write-once per physical session.
- MSI Afterburner must NOT start with Windows when CPU OC is active (causes login crash)
- BIOS update not recommended: P4.30F is stable, Z390 platform is mature, flash risk > benefit
