---
name: tplink-ax55-router-automation
related_skills: [router-admin-automation]
description: Use when changing TP-Link AX55 router settings.
tags: [router, tplink, network, playwright, automation]
---

# TP-Link AX55 Router Automation

## Key facts
- Router IP: 192.168.0.1
- Model: AX3000 4-Stream Wi-Fi 6 Router (Archer AX55)
- Firmware: 1.5.12 Build 20260521 (verified 2026-09-03; re-check device-state ref before assuming current). Blocks all raw HTTP POST requests to /login with HTTP 403 (CSRF protection). Do NOT attempt urllib/requests-based login. Use Playwright only.

## Why raw HTTP fails
The router returns bare HTTP 403 on all POST requests to `/login?form=*` from non-browser clients regardless of headers, cookies, or HTTPS. Firmware-level anti-scripting. Don't waste time trying to work around it.

## Working approach: Playwright headless Chromium

### Install (if not present)
```bash
pip3 install playwright --quiet
python3 -m playwright install chromium
```

### Login pattern
```python
import os
from playwright.sync_api import sync_playwright
import time

PASSWORD = os.environ.get('TPLINK_PASSWORD') or input('Router password: ')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(15000)

    page.goto('https://192.168.0.1/webpages/index.html', wait_until='domcontentloaded')
    time.sleep(3)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button:has-text("LOG IN")')
    time.sleep(5)  # wait for dashboard to load
```

## Known route hashes
Navigate with `page.goto('https://192.168.0.1/webpages/index.html#/<route>')` then `time.sleep(4)`:  (HTTPS required since 2026-09-03)

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
| `reboot` | Reboot router |
| `firmware` | Firmware update |
| `sysLog` | System log |
| `portForwarding` | NAT Forwarding > Port Forwarding (Virtual Servers) |

## Custom dropdown (su-select) pattern
Vue teleported dropdowns — standard `select` element doesn't exist. Pattern:

```python
def open_and_select(page, select_idx, option_text):
    su = page.query_selector_all('.su-select')
    su[select_idx].click()
    time.sleep(1.5)
    result = page.evaluate(f'''() => {{
        const placements = document.querySelectorAll(".su-dropdown-placement");
        for (let pl of placements) {{
            const rect = pl.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {{
                const opts = Array.from(pl.querySelectorAll("[role=option]"));
                const opt = opts.find(o => o.textContent.includes("{option_text}"));
                if (opt) {{ opt.click(); return {{clicked: true, text: opt.textContent}}; }}
            }}
        }}
        return {{clicked: false}};
    }}''')
    time.sleep(0.5)
    return result
```

## Input fields
DHCP and other pages: Vue inputs don't respond to `wait_for_selector` reliably. Always use `time.sleep(6)` after navigation, then mouse-click coordinates:

```python
page.mouse.click(737, <y>)
time.sleep(0.4)
page.keyboard.press('Control+a')
page.keyboard.type('new_value')
```

### DHCP Server field Y coordinates (1280x800 viewport)
| Field | Y |
|---|---|
| IP Pool Start | 330 |
| IP Pool End | 330 (x~870) |
| Lease Time (minutes) | 387 |
| Default Gateway | 431 |
| Primary DNS | 474 |
| Secondary DNS | 518 |

## Save button
Sticky footer at **(1059, 768)**. Use `page.mouse.click(1059, 768)`.
`button:has-text("Save")` locator fails — button text is uppercase `SAVE`.
Exception: on the Wireless Settings page, `page.locator('button:has-text("Save")').last.click()` works fine.

## WPA3 security (both bands)
```python
# 2.4GHz = su-select index 0, 5GHz = index 5 on wirelessSettingsAdv
open_and_select(page, 0, 'WPA3-Personal+WPA2-PSK[AES]')
open_and_select(page, 5, 'WPA3-Personal+WPA2-PSK[AES]')
page.locator('button:has-text("Save")').last.click()
time.sleep(6)
```
Note: WPA3 automatically disables WPS (router enforces this).

## Debugging
```python
page.screenshot(path='/tmp/router_debug.png')
# then: vision_analyze('/tmp/router_debug.png', ...)
```

## TP-Link AX55 Python API (tplinkrouterc6u)

AX55 uses AES-encrypted payloads. Direct `curl` returns `{"data":""}`. Always use the library:
```
pip3 install tplinkrouterc6u
from tplinkrouterc6u import TplinkRouterProvider
r = TplinkRouterProvider.get_client('http://192.168.0.1', 'PASSWORD')
r.authorize()
```

**Critical gotcha — partial writes silently ignored**: `r.set_wifi(Connection.HOST_2G, channel=N)` sends only `wireless_2g_channel=N`; AX firmware ignores single-field writes. Must use `r.request("admin/wireless?form=wireless_2g", full_data)` with ALL fields:
`operation=write&enable=on&ssid=...&hidden=...&encryption=...&psk_version=...&psk_cipher=...&psk_key=...&hwmode=...&htmode=...&channel=N&txpower=...&mu_mimo=...&airtime_fairness=...`

Radio briefly restarts after channel change — expect "No route to host" for 5–10 s, then reconnect. Verify: `iw dev <ifname> link | grep freq` (2412=ch1, 2437=ch6, 2462=ch11).

**Channel selection (AU)**: ch11 is worst (overlaps ch9-13). Prefer ch1 or ch6. Scan: `nmcli dev wifi list | awk 'NR==1 || / 1 /'`. In suburban AU, ch1 is often empty while ch6 is popular.

**DHCP enumeration**: `get_ipv4_dhcp_leases()` fails on AX55 (encrypted format mismatch). Use ping sweep + `ip neigh show` for MAC enumeration.

## Current router settings (as of 2026-08-16)
- SSID: 144McKinnonNetwork
- Security: WPA3-Personal+WPA2-PSK[AES] (both bands)
- WPS: Disabled (auto-disabled, incompatible with WPA3)
- Primary DNS: 1.1.1.1
- Secondary DNS: 1.0.0.1
- DHCP Lease Time: 1440 minutes (24h)
- Remote Management: Disabled (default)
