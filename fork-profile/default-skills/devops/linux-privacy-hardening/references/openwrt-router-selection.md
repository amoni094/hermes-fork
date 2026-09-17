# OpenWrt Router Selection — AU Home User Reference

Last updated: 2026-09-04
Context: replacing a TP-Link AX55 (AX3000, WiFi 6, 4x GbE LAN, USB 3.0) with
OpenWrt-capable hardware. Applies to AU home users wanting auditable firmware.

## Why OpenWrt matters for privacy/security

- Replaces closed-source vendor firmware entirely — no cloud callbacks, no telemetry
- Full nftables firewall scripting, proper VLANs (IoT isolation)
- WireGuard kernel module (faster than userspace), AdGuard Home, unbound
- Community security fixes often arrive faster than vendor patches
- After flashing: the router hardware manufacturer has zero ongoing involvement

## Current TP-Link situation (as of 2026)

- 7 US government agencies backed a ban on TP-Link routers; Commerce Dept concluded
  ban warranted for national security reasons (documented CCP-linked cyberattacks
  used TP-Link SOHO routers as pivot points)
- TP-Link AX55 V1 NOT officially supported by OpenWrt as of mid-2026
  (device tree merged into mainline kernel; proper support expected OpenWrt 25.12+)
- Flashing AX55 V1 with OpenWrt requires UART serial header soldering + TFTP —
  Ethernet and WiFi non-functional in current dev builds

## Recommended options (AU, 2025-2026)

### 1. Xiaomi AX3000T — TOP PICK for value

  Chip: MediaTek MT7981B (Taiwanese, not Chinese-owned; no documented backdoor)
  Specs: 1.3GHz dual-core, 256MB RAM, 128MB flash, WiFi 6 AX3000, 3x GbE LAN, 1x GbE WAN
  Missing vs AX55: no USB port
  OpenWrt: Official stable 24.10.2 support, one-step flash, clean ToH entry
  AU price: ~$43-60 AUD delivered (AliExpress Mijia store)
  OzBargain: https://www.ozbargain.com.au/node/852525

  China concern nuance:
  - Stock firmware: REAL concern — documented data collection, multiple RCE CVEs,
    slow patch cadence, cloud-connected management
  - After OpenWrt flash: Xiaomi firmware GONE; router is dumb hardware running
    auditable Linux. Zero Xiaomi involvement. The concern does not apply.
  - Hardware (MediaTek MT7981B): Taiwanese company, US/TW export controls, no
    documented backdoor. Widely used in OpenWrt-community-approved hardware.
  - Bottom line: the concern is real for stock firmware; irrelevant after OpenWrt flash.
    Your current TP-Link (US government ban backed by 7 agencies) is a worse position.

### 2. GL.iNet GL-MT3000 (Beryl AX) — Easiest path, ships with OpenWrt

  Chip: Same MediaTek MT7981B as Xiaomi AX3000T
  Specs: 2.5G WAN, GbE LAN x2 only (vs AX55's x4), USB 3.0
  Ships with: GL's OpenWrt-based firmware (good GUI); can flash vanilla OpenWrt
  AU price: ~$81-113 AUD (AliExpress ~$81, Amazon AU ~$103-113)
  OzBargain: https://www.ozbargain.com.au/node/952676 (watch for sales, goes to $82)
  Company: GL.iNet is HK-based, manufacturing in mainland China
  Best for: users who don't want to flash firmware themselves

### 3. Cudy WR3000E — Budget option with 2.5G WAN + USB

  Chip: MT7981B
  Specs: 2.5G WAN, 4x GbE LAN, USB 3.0, AX3000
  OpenWrt: Official support; version matters — WR3000E v1 has 2.5G WAN
  AU price: ~$50-80 AUD AliExpress
  Caveat: Less community testing than Xiaomi; verify version before buying

## If supply-chain hardware is the concern

All consumer routers are manufactured in China regardless of brand (ASUS, Netgear,
TP-Link, Xiaomi, GL.iNet). The only escape:

- Raspberry Pi 4/5 + USB WiFi adapter + OpenWrt: most auditable option
  Pi 4 manufactured in Wales; USB WiFi adapters vary
  Cost: ~$80-120 AUD + effort; not plug-and-play
  Best for: high-assurance setups where hardware supply chain is the specific threat

## Decision guide

  Want cheapest + best OpenWrt support? -> Xiaomi AX3000T (~$50)
  Want USB port + easiest setup?        -> GL-MT3000 (~$81-113)
  Need 4 LAN ports + USB on a budget?  -> Cudy WR3000E (~$50-80)
  Hardware supply chain is the threat?  -> Raspberry Pi 4/5 + OpenWrt

## Sources

- OpenWrt forum: https://forum.openwrt.org/t/best-newcomer-router-2025/222871
- OzBargain Xiaomi: https://www.ozbargain.com.au/node/852525
- OzBargain GL-MT3000: https://www.ozbargain.com.au/node/952676
- Reuters / WaPo on TP-Link ban: US Commerce Dept interagency risk assessment 2025
- Thalium research: RCE CVEs on Xiaomi stock firmware (LAN+WAN)
- MediaTek MT7981B: no documented backdoor; Taiwanese company, audit available
