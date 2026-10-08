# Home Network Advisory — Router Selection, WiFi, and Gateway Architecture

## Router selection for OpenWrt compatibility

When recommending an OpenWrt-compatible router to replace a mid-range consumer router (e.g. TP-Link AX55):

### Decision criteria
- OpenWrt pre-installed = no brick risk, no warranty void (preferred over manual flash)
- WiFi driver maturity matters — community-supported drivers for newer chipsets (WiFi 6/7 Qualcomm/MediaTek) can have quirks; check the OpenWrt ToH page for the specific model before recommending
- 2.5GbE ports are future-proof for NBN upgrades and useful for wired Pi/desktop connections
- Built-in AdGuard Home (GL.iNet firmware) can replace or supplement Technitium on the Pi — reduces dependency on Pi for DNS blocking

### GL.iNet lineup (ships with OpenWrt-based firmware, officially supported)

| Model | WiFi | Max throughput | Ports | Notes |
|---|---|---|---|---|
| Beryl AX (GL-MT3000) | WiFi 6 AX3000 | ~600Mbps WG | 1x 2.5GbE WAN, 2x GbE LAN | Good for apartments, cheaper |
| Flint 2 (GL-MT6000) | WiFi 6 AX6000 | ~900Mbps WG | 1x 2.5GbE WAN, 4x GbE LAN | Best value WiFi 6 OpenWrt pick |
| Flint 3e (GL-BE6500) | WiFi 7 BE6500 | ~1100Mbps WG | 5x 2.5GbE | WiFi 7 + MLO; good price when on sale |

Flint 3e advantages over Flint 2 for this user's setup:
- WiFi 7 MLO (Multi-Link Operation) improves range through obstacles — relevant for apartment with 1-bar study signal
- Preamble Puncturing reduces interference in apartment buildings (dense competing WiFi)
- 5x 2.5GbE: Pi + desktop both wired without USB adapter
- Built-in AdGuard Home and Tailscale
- Same GL.iNet OpenWrt base = same nftables access

Caveat: GL.iNet firmware is OpenWrt-based but not stock OpenWrt — their UI skin is on top. WiFi 7 speed peaks only realized with WiFi 7 clients; range/stability improvements from better radio hardware apply regardless.

### Stock OpenWrt via manual flash (higher risk)

- Always check openwrt.org/toh for the exact model + hardware version before proceeding
- Wrong regional firmware image can brick the router — download only from manufacturer's regional page
- ASUS with Merlin firmware is a safer middle ground: keeps ASUS UI, adds proper firewall rules and WireGuard

### TP-Link AX55 limitations (current router)
- Firewall UI is toggle-only — no custom rule editor, no per-device port rules
- Access Control is MAC-based only (deny list by MAC, not by port or protocol)
- OpenWrt support for AX55 is partial at best — WiFi 6 drivers are community-maintained
- Recommendation: replace rather than flash if OpenWrt rules are needed

## Pi-as-gateway tradeoffs

Before recommending the Pi as a network gateway (all traffic flows through it):

### Hardware requirement
Pi 3B+ has one network interface. Being a true gateway requires two — one WAN-facing, one LAN-facing. Options:
- USB-to-ethernet adapter (~$10-15 AUD) as second interface — shared USB bus, caps real throughput ~200-300Mbps combined
- Single-homed Pi with router routing through it — messier, router support varies, AX55 may not support custom default gateway in DHCP settings

### Performance cap
Pi 3B+ ethernet is 100Mbps max (shared USB bus with WiFi). If internet is under ~100Mbps NBN, invisible. Above 100Mbps NBN, the Pi becomes the bottleneck for all network traffic.

### Reliability cost
Pi as DNS-only: Pi crash = DNS breaks, internet still works.
Pi as gateway: Pi crash = entire network loses internet. This is the primary reason NOT to use Pi as gateway on a flat home LAN.

### When it IS worth it
- Internet speed is under 100Mbps
- User needs per-device iptables rules that the router cannot provide
- User accepts the reliability tradeoff and has a fallback plan

### Preferred alternative
Keep Pi as DNS-only. Use Technitium DoH domain blocklist to intercept rogue DNS at the DNS layer. Get a router with proper firewall (GL.iNet OpenWrt) for port-level rules. This separates concerns and avoids the gateway single-point-of-failure.

## WiFi signal diagnosis — apartment

For 1-bar WiFi in a study with one wall + TV obstacle between router and device:

### Diagnosis priority order
1. **Placement first** — router tucked behind TV, in a cabinet, or at one end of the apartment is the most common cause. Elevate to a shelf, pull away from obstacles. Try before buying anything.
2. **Band check** — 5GHz degrades badly through metal obstacles (TV chassis is metal). Try forcing device to 2.4GHz if signal is unstable. 2.4GHz penetrates walls/obstacles better; slower but more reliable at distance.
3. **Wired AP in study** — single ethernet cable from router to study + cheap AP (TP-Link EAP225/EAP670). Best outcome; cable runs along skirting board invisibly.
4. **Powerline + AP** — if cable is impossible, powerline adapter pair (~$80-150 AUD). Works well in apartments where wiring shares one switchboard.
5. **Mesh node** — wired backhaul preferred; wireless backhaul cuts bandwidth ~50% but still beats 1-bar WiFi.
6. **New router** — only if all above fail or combined with router upgrade for other reasons.

### WiFi generation vs signal strength
WiFi 7 and WiFi 6 hardware (better antennas, MLO, Preamble Puncturing) genuinely improve range even when clients are older WiFi generations — the radio hardware improvement is real regardless of protocol version.

WiFi generation only matters for peak throughput when BOTH router AND client support it.

### Device WiFi capability detection

Check from terminal on the current host:

    lspci | grep -i -E 'network|wifi|wireless'
    # Intel Wi-Fi 6 AX201 = WiFi 6 confirmed
    # Intel Wi-Fi 6E AX211 = WiFi 6E
    # Qualcomm WCN7850 / MediaTek MT7921 = WiFi 6/6E

Windows (remote via SSH or PowerShell):

    netsh wlan show drivers | findstr "Radio types"
    Get-NetAdapter | Select Name, InterfaceDescription, LinkSpeed

macOS:

    system_profiler SPAirPortDataType | grep "Supported PHY Mode"

Known device WiFi capabilities for this network:
- Laptop (Intel AX201, wlp0s20f3, MAC 10:3d:1c:ea:38:3c): WiFi 6
- Pixel 8a: WiFi 6
- AX55 router: WiFi 6 (AX3000)
- Pi 3B+: WiFi 4 (2.4GHz only — 802.11n)
- PS5: WiFi 5 (802.11ac)
- LG TV 192.168.0.107: WiFi 5 at best
- Apple device 192.168.0.114: WiFi 6 if iPhone 12+/MacBook Air M1+
- Desktop DESKTOP-PH4F2DK: confirm via `Get-NetAdapter` (likely WiFi 6 Intel card)

## Router DHCP DNS — force all devices to Pi

TP-Link AX55 path: Advanced > Network > DHCP Server
- Primary DNS: 192.168.0.138 (Pi)
- Secondary DNS: blank or 0.0.0.0 — do NOT set a public resolver; ~50% of queries will bypass Pi if secondary is set

Router's own WAN DNS (for router firmware updates, NTP, TP-Link cloud): Advanced > Network > Internet (WAN settings). Set to 192.168.0.138 or a public resolver (9.9.9.9) — this only affects the router itself, not LAN clients.

Verify Pi is receiving queries: Technitium dashboard → Top Clients. Any device not appearing there is bypassing the Pi.

### AX55 DoT setting location

Advanced > Network > Internet (the Advanced Settings page, not the Basic internet page). The DoT/DoH section appears as a radio group with options: DoT / DoH / None. Set to None to ensure DNS goes through the Pi rather than encrypted directly to an upstream provider. With DoT enabled, even if DHCP hands clients the Pi's IP, the router's own upstream DNS bypasses the Pi entirely.

## NBN / ISP topology

This user's NBN connection: HFC (Hybrid Fibre-Coaxial) via Launtel. Modem: Arris CM8200B P2 (DOCSIS 3.1). The CM8200B is a bridge-mode modem only — no routing, no DNS, no admin UI accessible from LAN (192.168.100.1 is firewalled by NBN Co firmware). Router WAN IP: 203.12.11.199 (dynamic). ISP gateway: 203.12.0.1 (launtel.au).

Traceroute from router Diagnostics tool: hop 1 = ISP gateway (not a local modem hop). No intermediate modem management interface exists between the router WAN port and the NBN NTD.

Launtel privacy posture: independent Australian ISP, no data harvesting, no DNS hijacking. Subject to Australian mandatory metadata retention (2 years: IPs, times, volumes — not content). DNS queries protected by Pi + encrypted upstream. HTTPS content not visible to ISP.

## Browser HTTPS-Only Mode

To prefer HTTPS for all browsing when available:
- Firefox: Settings > Privacy & Security > HTTPS-Only Mode > Enable for all windows
- Chrome/Edge: Settings > Privacy and security > Security > Always use secure connections

This is a browser-level setting; no router or DNS config achieves equivalent coverage. HSTS preload lists (active by default in Firefox/Chrome) enforce HTTPS for major sites regardless of this setting.
