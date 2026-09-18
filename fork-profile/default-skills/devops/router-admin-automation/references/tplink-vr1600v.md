# TP-Link Archer VR1600v — Session Notes (2026-09-02)

## Hardware
- Model: Archer VR1600v V2 (AC1600 Wireless Dual Band Gigabit VoIP VDSL/ADSL Modem Router)
- MAC OUI: 98:DA:C4 = TP-LINK TECHNOLOGIES CO.,LTD.
- LAN IP: 192.168.1.1
- Default credentials: admin / admin (factory default, unchanged)

## Firmware upgrade performed
- Pre: 0.1.0 0.9.1 v5006.0 Build 220518 Rel.32480n (May 2022)
- Post: 0.1.0 0.9.1 v5006.0 Build 260317 Rel.7757n (March 2026)
- ~4 years of updates applied in one shot

## AU firmware download
- Page: https://www.tp-link.com/au/support/download/archer-vr1600v/v2/
- File: `Archer_VR1600vV2_0.1.0_0.9.1_up_boot(260317)_2026-03-17_10.25.18.bin.zip`
- URL pattern: `https://static.tp-link.com/upload/firmware/<YEAR>/<YYYYMM>/<YYYYMMDD>/<file>.zip`
- Extracted .bin size: ~26 MB
- Zip header offset warning is harmless; `unzip -o` extracts fine with exit 1

## Upload/flash traffic sequence
1. `POST /cgi/softup` — multipart upload of .bin
2. `GET /cgi/softburn` — triggers actual flash write (must not be interrupted)
3. Router goes dark for ~60-90s
4. Router comes back at login page — flash complete

## What went wrong first attempt
Script set 15s timeout and closed the browser when progress bar hit ~90%.
This cut the HTTP connection before `/cgi/softburn` finished. Router stayed on old firmware.
Fix: keep the Playwright session alive via try/except on `page.screenshot()` until exception.

## Advanced menu structure (confirmed post-firmware-upgrade)
Basic tab: Network Map, Wireless, Guest Network, PPPoE, USB Sharing, Parental Controls
Advanced tab: Status, Network, Wireless, Guest Network, NAT Forwarding, USB Sharing,
  Parental Controls, Bandwidth Control, Security,
  System Tools > Time Settings, LED Control, Diagnostics, Firmware Upgrade,
                  Backup & Restore, Reboot, Administration, System Log,
                  CWMP Settings, SNMP Settings, Traffic Monitor

## Online upgrade
`#t_onLineUpgrade` button was not visible — router could not reach TP-Link update server
or requires a cloud account. Local upgrade is the reliable path.

## Firmware version string format
`Firmware Version:0.1.0 0.9.1 v5006.0 Build YYMMDD Rel.NNNNn`
Read from firmware page text after logging in via Advanced > System Tools > Firmware Upgrade.

## Settings audit applied (2026-09-02 post-firmware)

| Setting | Before | After |
|---|---|---|
| Firmware | Build 220518 (2022) | Build 260317 (2026) |
| DNS Primary | 0.0.0.0 | 1.1.1.1 |
| DNS Secondary | 0.0.0.0 | 1.0.0.1 |
| 2.4GHz channel | Auto | 6 |
| 2.4GHz width | Auto | 20MHz |
| DoS Protection | Disabled | Enabled |
| NTP Server II | 0.0.0.0 | time.cloudflare.com |
| Admin password | admin (default) | TPLink@2026 |

Note: WPS was not disabled (visible in Advanced > Wireless > Advanced Settings but
the toggle is at the global level, not per-session; left for owner to decide).

## UI widget quirks on VR1600v vs AX55

### Dropdowns: tp-select (not su-select)
- AX55 uses `.su-select` with `.su-dropdown-placement` portal divs
- VR1600v uses `.tp-select > .select-box` with direct `<li>` children visible in the page
- Open by `page.mouse.click(x, y)`, then click the `<li>` by coordinate or JS text match
- Channel 6 appears at y≈688 when dropdown opened from y≈435 (1280x800)

### Button-group toggles: button-group-cover intercepts clicks
- `page.click('#enableDoSProtectionOn')` times out: `<ul class="button-group-cover">` overlays
- Fix: `btn.dispatchEvent(new MouseEvent('click', {bubbles: true}))` via JS

### DNS/IP fields: octet-split, no IDs
- Four `<input>` elements per IP address, x-sorted, grouped by Y coordinate
- Primary DNS at y≈639, Secondary DNS at y≈676 on LAN settings page (1280x800)
- Set via JS: read Y groups, then set `.value` + dispatch `input` + `change` events

### Admin password form
- Field IDs: `curName`, `curPwd`, `newName`, `newPwd`, `cfmPwd`
- Error 84602 = `newName` was blank — MUST fill username even if keeping same value
- Success = form clears (no dialog), page returns to normal state
