# TP-Link Archer AX55 UI notes

Concise field notes for reviewing Archer AX55 router posture in a live browser session.

## Reliable navigation pattern
- The AX55 web UI is a SPA. Direct `#/route` navigation is often more reliable than sidebar clicks when browser automation loses state.
- Useful routes observed live:
  - `#/administration`
  - `#/firewall`
  - `#/wps`
  - `#/ipv6`
  - `#/accessControl`
- If refs suddenly fail or the page becomes blank, assume the browser session reset. Re-open `http://192.168.0.1/webpages/index.html#/administration`, log in again, and continue.

## Administration page findings
Observed on an AX55 during a live review:
- `Local Management via HTTPS` toggle present
- `Local Managers` selector present
- `Remote Management` toggle present
- No visible separate WAN HTTP/HTTPS selector in the main Administration page
- No visible web-management-port or source-IP restriction field in the main Administration page snapshot

Practical interpretation:
- Do not assume remote HTTP can be enabled just because older TP-Link docs mention web management ports.
- On this firmware family, absence of the HTTP option may mean remote admin is effectively HTTPS-only.
- Phrase conclusions carefully: `appears HTTPS-only on this firmware` unless you directly verify the external URL/port behavior.

## Firewall page findings
Observed toggles:
- `SPI Firewall`
- `Respond to Pings from LAN`
- `Respond to Pings from WAN`

Practical baseline:
- SPI Firewall: ON
- Respond to WAN pings: OFF
- Respond to LAN pings: optional, not security-critical for a normal home LAN

## Other high-value checks
- WPS page exposes a single WPS enable/disable switch; disable it for normal home use.
- Wireless page may show WPA2-PSK[AES]; prefer WPA2/WPA3 mixed or WPA3 when all clients support it.
- UPnP can be acceptable for PS5 / casual gaming if DMZ stays off and manual forwards stay minimal.

## External references worth consulting
- TP-Link FAQ 1553 (`Set Up Remote Management on TP-Link Routers`) documents generic TP-Link remote-management concepts but may reflect older/model-dependent HTTP examples.
- TP-Link community thread `Archer AX55 remote management with HTTP port 80 non available` supports the model-specific inference that AX55 firmware may expose HTTPS-only remote management.
