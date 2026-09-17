# TP-Link Archer AX55 — Device Reference

## Hardware
- Model: Archer AX55 v1.0 (AX3000 4-Stream Wi-Fi 6 Router)
- Firmware: 1.5.12 Build 20260521 (latest as of 2026-09-03)
- Router IP: 192.168.0.1 (HTTPS only since 2026-09-03)
- WAN MAC: A8-42-A1-3C-9C-25
- Public IP: 203.12.11.199 (CGNAT — inbound port forwards are non-functional)
- ISP: Launtel (AU)
- SSID: 144McKinnonNetwork; DDNS: 144mckinnon.servecounterstrike.com

## Settings as of 2026-09-03
| Setting | Value |
|---|---|
| Security (both bands) | WPA3-Personal+WPA2-PSK[AES] |
| WPS | Disabled (WPA3 incompatible) |
| Primary DNS (DHCP) | 1.1.1.1 |
| Secondary DNS (DHCP) | 1.0.0.1 |
| DNS Privacy (DoT) | ENABLED — NextDNS profile f134dc |
| DoT Primary | 45.90.28.0 (NextDNS Sydney) |
| DoT Secondary | 45.90.30.0 |
| DHCP Lease Time | 1440 minutes (24h) |
| Remote Management | Disabled |
| Local Management | HTTPS only |
| SPI Firewall | On |
| Respond to Pings (WAN) | Off |
| UPnP | DISABLED (2026-09-03) |
| WoL Port Forward | DELETED (was UDP 47293 → .181:9) |
| IPv6 | DISABLED |

## Connected devices (2026-09-03)
| IP | MAC | Identity | Notes |
|---|---|---|---|
| .107 | 44-27-45-82-07-6A | LG TV (LGwebOSTV) | 2.4G; Miracast target |
| .129 | 64-90-C1-88-36-72 | Xiaomi air purifier (zhimi-airpurifier-mb3) | 2.4G; IoT isolation recommended |
| .140 | 2C-9E-00-19-EA-2F | PlayStation 5 | Sony IE OUI confirmed; no reverse DNS |
| .156 | 56-3B-90-48-5F-71 | Mobile phone (Pixel 8a) | Randomised MAC; offline 2026-09-03 |
| .165 | 0E-10-98-C9-DE-55 | iPhone | Randomised MAC |
| .181 | 70-D8-C2-70-0D-B4 | Windows desktop DESKTOP-PH4F2DK | Reserved; offline 2026-09-03; Teredo disable pending |
| .185 | 10-3D-1C-EA-38:3C | ThinkPad (this machine, fedora.local) | Intel NIC; 0.07ms RTT |

## DoT verification
```bash
# Confirm DoT routing through NextDNS
dig @192.168.0.1 +short dns.nextdns.io   # should return NextDNS IPs
curl -s https://ipinfo.io/$(dig @192.168.0.1 +short whoami.ds.akahelp.net TXT | tr -d '"' | awk '{print $2}')
# Expected: hostname = dns.nextdns.io, org = NextDNS, region = AU
```
Confirmed resolver 2026-09-03: 207.148.84.39 = dns.nextdns.io Sydney.

## NextDNS profile f134dc
- Avira telemetry block: add `safethings.avira.com` to denylist (exact subdomain, free tier has no wildcards)
- Verify block: `dig @192.168.0.1 safethings.avira.com` — should return NXDOMAIN when denylist entry is active

## Known route hashes
| Route | Page |
|---|---|
| `wirelessSettingsAdv` | Wireless security (WPA3, passwords) |
| `wps` | WPS enable/disable |
| `dhcpServer` | DHCP pool, lease time, DNS |
| `administration` | Change password, Remote Management (scroll down) |
| `upnp` | UPnP enable/disable |
| `accessControl` | Access control |
| `firewall` | Firewall settings |
| `tpLinkCloud` | TP-Link cloud/ID |
| `reboot` | Reboot |
| `firmware` | Firmware update |
| `sysLog` | System log |
| `portForwarding` | Port Forwarding (Virtual Servers) |

Note: DoT/DoH setting has NO hash route — use in-UI search (see router-admin-automation SKILL.md DoT section).

## Pending
- Xiaomi air purifier: move to Guest network or enable Device Isolation
- Avira denylist entry: confirm in NextDNS dashboard
