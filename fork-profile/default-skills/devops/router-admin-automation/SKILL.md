---
name: router-admin-automation
related_skills: [tplink-ax55-router-automation]
description: "Use when automating consumer router or LAN device admin UI via Playwright, or auditing and securing LAN devices (routers, printers, IoT)."
tags: [router, network, playwright, browser-automation, TP-Link, devops]
---

# Router Admin Automation via Playwright

## When to use

Consumer router firmware from ~2022+ (TP-Link AX-series, Asus AX-series, Netgear Nighthawk) blocks raw HTTP POST to login and settings endpoints — bare HTTP 403 with empty body regardless of headers, cookies, HTTPS, or Origin spoofing. The only reliable path is a real browser via Playwright.

Use this skill for:
- LAN device discovery and inventory
- Wireless security changes (WPA2 → WPA3, disable WPS)
- Setting DHCP DNS servers for all clients
- Firmware auditing and updating for LAN-connected devices (routers, printers)
- Any router or LAN device admin task the user doesn't want to do manually

Do NOT attempt raw urllib/requests for login on modern firmware — it will 403 unconditionally.

## LAN device discovery

When the user asks to scan the LAN or find devices:

```bash
# 1. Confirm subnet
ip route show | grep 'proto kernel'
# e.g. 192.168.0.0/24 dev wlp0s20f3

# 2. Ping sweep (populate ARP cache)
for i in $(seq 1 254); do ping -c 1 -W 1 192.168.0.$i &>/dev/null & done
wait; sleep 2

# 3. ARP cache — live devices only
arp -n | grep -v incomplete

# 4. Confirm specific IPs with arping (gets MAC even if ICMP is filtered)
arping -c 2 -I wlp0s20f3 192.168.0.X 2>/dev/null | grep -o '\[.*\]'
```

ARP gives MAC OUIs — identify vendors with `https://api.macvendors.com/<mac>` (rate-limit: one at a time; 429 means slow down).

For hostnames and fuller inventory, log into the Telstra modem (192.168.0.1) and read the DHCP client list at `/owl_lan_device.htm?m=basic` — it shows IP, hostname, link speed, and per-device detail pages at `/client.htm?clientip=X.X.X.X&m=basic`.

See `references/telstra-modem-device-map.md` for this-network's known device inventory.

## LAN device security audit

When asked to secure and update LAN devices, work through this checklist after scanning:

1. **Identify everything first.** OUI alone is often wrong (Mitsumi OUI on the Sony TV; Quectel OUI on the Tesla gateway). Combine: OUI + open ports + TLS cert CN + HTTP page title + UPnP XML.

2. **Triage what's actionable.** Most consumer IoT cannot be touched remotely:
   - Cloud-only devices (Eufy, Amazon Echo/Fire TV): auto-updated by vendor, no local interface. No action.
   - Vendor-managed OTA (Tesla Powerwall gateway): Tesla controls firmware. No action.
   - EOL devices (Sony Bravia pre-2013): no updates exist. Document and accept risk.
   - Devices with web UI: check for open access control, outdated firmware, insecure protocols.

3. **For each device with a web UI, check in order:**
   - Is admin login password-protected? (LinkTap GW-02 ships with access control OFF)
   - Is firmware current? (check against vendor support page)
   - Are unnecessary protocols disabled? (FTP server, TFTP, Telnet, raw SMTP server)
   - Is HTTPS enforced for admin? (Brother: yes; LinkTap: no HTTPS available)
   - TLS version: prefer TLS 1.2+ only

4. **IoT device fingerprinting by port signature:**
   | Ports open | Likely device |
   |---|---|
   | 52323 (UPnP/DLNA) | Sony Bravia (pre-2013 DLNA renderer) |
   | 55442, 55443, 8009 | Amazon Echo or Fire TV |
   | 80 only, no auth | LinkTap GW-02 or similar IoT gateway |
   | 443 only, self-signed Tesla cert | Tesla Energy/Powerwall gateway |
   | 80+443, Brother HTML, password-only login | Brother printer web UI |
   | No open ports, ping responds | Cloud-only hub (Eufy HomeBase) |

5. **TLS cert check for unidentified HTTPS devices:**
   ```bash
   echo | openssl s_client -connect 192.168.0.X:443 -servername 192.168.0.X 2>/dev/null \
     | openssl x509 -noout -subject -issuer -dates 2>/dev/null
   ```
   The `O=` and `CN=` fields often name the manufacturer directly (e.g. `O=Tesla Energy Products`).

6. **LinkTap GW-02 access control:** no script — do it in the browser at http://192.168.0.2, bottom of page, 'Access settings'. Firmware updates only via the phone app.

7. **Report format:** for each device, state: current state, action taken or reason no action, result. Do not report success without verifying the change (re-read firmware version, confirm login now requires a password, etc.).

## Prerequisites

```bash
pip3 install playwright
python3 -m playwright install chromium
```

## Core pattern

### Step 0: Check memory before touching the network
If the user says "I was on that LAN earlier" or names a person's network, call `hindsight_recall` with a person-scoped query (e.g. "Natasha network router gateway IP") before attempting SSH or a subnet scan — the gateway IP is often already in memory from the prior session and scanning is wasteful when it is.
Only proceed to live discovery if memory returns nothing useful.

Discover the LAN gateway first (`ip route show default`). Do not assume `192.168.0.1`.
This household AX55 is **HTTPS-only** at `192.168.0.1` (this-router-only) — HTTP login/settings fail there.
Post-login wait on AX55 is **≥7s** (5s is not enough). Later hash navigations still need 3–5s for Vue hydration.

```python
from playwright.sync_api import sync_playwright
import time

def w(secs=2):
    time.sleep(secs)

GATEWAY = 'https://192.168.0.1'  # this-LAN AX55; replace after discovering the gateway

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--ignore-certificate-errors']   # required for HTTPS routers
    )
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(15000)

    page.goto(f'{GATEWAY}/webpages/index.html', wait_until='domcontentloaded')
    w(3)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button:has-text("LOG IN")')
    w(7)    # AX55 dashboard; 5s is not enough

    # Navigate via hash route
    page.goto(f'{GATEWAY}/webpages/index.html#/wirelessSettingsAdv',
              wait_until='domcontentloaded')
    w(4)    # Vue hydration is async; always wait before querying

    browser.close()
```

## TP-Link AX-series (AX3000 / AX55 / AX73)

### Firmware anti-automation
- Login endpoint (`/login?form=login`, `/login?form=initial_login`) returns HTTP 403 for all non-browser HTTP clients.
- The firmware implements RSA + AES-CBC + HMAC-SHA256 crypto. Do not attempt to replicate it — use Playwright.
- Auth/keys endpoints (`/login?form=auth`) do respond to raw HTTP (they serve public keys). Only the login POST is blocked.

### SPA navigation
- Root URL: `/webpages/index.html`; settings are hash routes: `#/wirelessSettingsAdv`, `#/wps`, `#/dhcpServer`, `#/lan`
- After login on AX55, wait **≥7s**. After later hash `goto()`, wait 3–5s. Vue hydrates asynchronously; querying early returns 0 elements.

### Custom dropdown (su-select) — KEY PITFALL
TP-Link uses a Vue component (`su-select`) that renders options in a **teleported portal div** detached from the select's DOM parent. Standard `page.select_option()` does NOT work. Use:

```python
def select_su_option(page, select_index, option_text):
    su_selects = page.query_selector_all('.su-select')
    su_selects[select_index].click()
    time.sleep(1.5)   # wait for portal animation
    result = page.evaluate(f'''() => {{
        const placements = document.querySelectorAll(".su-dropdown-placement");
        for (let i = 0; i < placements.length; i++) {{
            const rect = placements[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {{
                const opts = Array.from(placements[i].querySelectorAll("[role=option]"));
                const opt = opts.find(o => o.textContent.includes("{option_text}"));
                if (opt) {{ opt.click(); return {{clicked: true, text: opt.textContent}}; }}
            }}
        }}
        return {{clicked: false}};
    }}''')
    return result
```

### Save buttons
- The SAVE button label is uppercase `SAVE` — `button:text("Save")` fails. Use `button:has-text("Save")` or `page.mouse.click(x, y)`.
- DHCP/LAN: SAVE is in a sticky footer. Click by pixel coordinate (see reference table below).
- After wireless save: wait 5-6 s — firmware restarts the wireless subsystem.

### WPA3 side effect
Setting WPA3-Personal+WPA2-PSK[AES] automatically disables WPS (router shows WPS as disabled/incompatible). No separate WPS toggle needed.

### Input filling on DHCP page
Vue text inputs can ignore Playwright `.fill()` before full hydration. Use mouse clicks at pixel coords:

```python
page.mouse.click(737, 474)    # Primary DNS field
time.sleep(0.4)
page.keyboard.press('Control+a')
page.keyboard.type('1.1.1.1')

page.mouse.click(737, 518)    # Secondary DNS field
time.sleep(0.4)
page.keyboard.press('Control+a')
page.keyboard.type('1.0.0.1')

page.mouse.click(1057, 768)   # SAVE button
```

### Session continuity
After saving WPA3, navigate each subsequent settings section in a fresh browser session to avoid Vue router state issues.

## Verification

Take a screenshot after each save and inspect with `vision_analyze` — do NOT rely on `page.evaluate()` returning correct values immediately after save (Vue re-render makes inputs appear empty transiently).

```python
page.screenshot(path='/tmp/verify.png')
# then: vision_analyze(image_url='/tmp/verify.png', question='...')
```

Use `page.inner_text('body')` (not evaluate-based DOM queries) for post-save body text verification.

## Coordinate reference (this-router AX55, 1280×800 viewport only)

Pixel coords are this-viewport/this-firmware. Re-screenshot before using. Do not treat as general TP-Link advice.

| Element            | X    | Y    |
|--------------------|------|------|
| Primary DNS field  | 737  | 474  |
| Secondary DNS field| 737  | 518  |
| SAVE button        | 1057 | 768  |
| 2.4GHz su-select   | index 0 | — |
| 5GHz su-select     | index 5 | — |

Coordinates shift if the sidebar expands/collapses — screenshot + `vision_analyze` to verify before relying on hardcoded coords.

## Common pitfalls

- `wait_for_selector('input[type=text]')` times out on DHCP page if called before Vue hydration. Use explicit `time.sleep(4)`.
- `keyboard.select_all()` does not exist in Playwright Python — use `keyboard.press('Control+a')`.
- Hash navigation does not trigger `wait_until='networkidle'` reliably. Always add explicit sleep.
- Portal options are outside the select's parent DOM — parent-relative selectors fail.
- `page.evaluate()` returning empty inputs post-save is a false negative — verify visually via screenshot.
- Post-login sleep must be at least 7 s — 5 s is not enough for the AX55 dashboard to fully hydrate.

### Toggle state ambiguity (AX55 — critical)
`document.body.innerText` extracts the *label text* next to checkboxes, not their checked state.
On the Administration page, `"Remote Management\nEnabled"` is the label — NOT an indication the feature is on.
Do NOT infer toggle state from the word "Enabled" appearing in extracted text. Instead:
  - Use `page.screenshot(path=...) + vision_analyze(...)` to read toggle colour (cyan = on, grey = off), OR
  - Query `page.evaluate("() => [...document.querySelectorAll('input[type=\"checkbox\"]')].map(c=>({checked:c.checked}))")` for raw checked state.

### DoS Protection route (this-router AX55; last checked on FW 1.5.12 — re-verify hashes after upgrade)
The `dosProtection` hash does NOT route to the DoS settings page — it falls back to the network map.
DoS Protection moved into the HomeShield section in recent firmware; navigate via HomeShield menu, not a direct hash.

## DoT/DoH configuration (this-router AX55; last checked on FW 1.5.12)
No direct hash route. Use in-UI search to navigate:
1. Click search icon (top nav, ~x=904, y=35 on **1280x900** viewport — not the 1280x800 DHCP coords above)
2. Search 'DoH', click SEARCH
3. Click 'Advanced > Network > Internet > DoT/DoH' result (~x=328, y=461)
4. DoT section is below fold — use JS scrollIntoView to bring radios into view
5. Radios: index 0=DoT, index 1=DoH, index 2=None. Select via:
   `page.evaluate("""() => { const r=document.querySelectorAll('input[type=radio]'); r[0].closest('label').click(); }""")`
6. Three DNS server inputs appear (y≈493/537/581 in scrolled view, width>200)
7. Fill via JS dispatch: set .value, fire 'input'+'change' events
8. Click SAVE button

DoT server IPs, NextDNS profile id, and resolver checks are this-router live state — read `references/tplink-ax55-device-state.md`, do not copy them as general NextDNS advice.
Confirm DoT is active with `dig @<gateway> +short dns.nextdns.io` (expect NextDNS IPs).
NextDNS free tier denylist is exact-subdomain only (no wildcards).

### Security audit page order (AX55)
For a full security audit, check these routes in order:
1. `wirelessSettingsAdv` — WPA3, SSID hide
2. `wps` — confirm disabled
3. `administration` (full_page screenshot) — Remote Management, Local HTTPS mgmt, password recovery
4. `upnp` — toggle state AND client list for unexpected external port mappings
5. `firewall` — SPI on, WAN/LAN ping off
6. `tpLinkCloud` — confirm not linked
7. `portForwarding` — review all active rules
8. `firmware` — confirm up to date
9. `dmz` — confirm disabled
10. HomeShield section — DoS protection (not reachable via hash)
For the administration page, scroll all the way down or use `full_page=True` on screenshot — Remote Management is below the fold.

### Live AX55 inventory (this-router-only; do not guess hardware state)
See `references/tplink-ax55-device-state.md` for firmware, DHCP/MAC map, NextDNS profile, and pending isolation. Do not duplicate those facts here.
Snapshot facts that change automation:
- Admin UI is **HTTPS-only**. HTTP login/settings fail; keep Playwright `--ignore-certificate-errors`.
  <!-- why: prevents HTTP 403/empty-page loops on AX55 after local-HTTPS-only was enabled -->
- WAN is CGNAT — inbound port forwards are non-functional. Do not re-add them expecting inbound reachability. WoL port-forward details live in `wake-on-lan-desktop`, not here.
  <!-- why: prevents wasting a session restoring port-forwards that cannot work behind CGNAT -->
- Extra hash routes not on the audit list: `accessControl`, `reboot`, `sysLog`. IPv6 is disabled on this unit.

## TP-Link Archer VR1600v (VDSL/ADSL modem-router)

Different model family from the AX-series. See `references/tplink-vr1600v.md` for full session detail.

### Key differences from AX55
- Default LAN IP: **192.168.1.1** (not 192.168.0.1)
- Default credentials: `admin` / `admin` (confirmed on factory-default unit)
- Login form IDs: `#pc-login-user`, `#pc-login-password`, `#pc-login-btn`. Do not assume AX55 uses these — AX55 automation uses `input[type=password]` + `LOG IN`.
- Uses `/cgi/softup` + `/cgi/softburn` for firmware upload (not a hash route)
- No online upgrade if the router can't reach TP-Link servers — use local upgrade only

### Router fingerprinting (no auth required)
```bash
curl -s -L http://192.168.1.1 | grep modelName
# Returns: var modelName="Archer VR1600v"; var modelDesc="AC1600 ..."
```
Also reliable: MAC OUI lookup — `98:DA:C4` prefix = TP-Link.

### Conflicting session dialog
If another device is already logged in, a modal blocks. The "take over" button is `#confirm-yes`:
```python
confirm = page.query_selector('#confirm-yes')
if confirm and confirm.is_visible():
    confirm.click()
    time.sleep(5)
```

### Navigation to Firmware Upgrade
The `#firmware` hash route returns 403 on this model. Use the menu:
```python
page.click('#advanced')
time.sleep(3)
for link in page.query_selector_all('a.click'):
    if link.is_visible() and 'System Tools' in (link.inner_text() or ''):
        link.click(); time.sleep(2); break
for link in page.query_selector_all('a.click'):
    if link.is_visible() and 'Firmware Upgrade' in (link.inner_text() or ''):
        link.click(); time.sleep(5); break
```

### Local firmware upgrade — CRITICAL pitfall
The upload goes to `/cgi/softup`, then `/cgi/softburn` triggers the actual flash write.
**If the browser closes or the script exits before `/cgi/softburn` completes, the flash
is aborted and the old firmware stays.** Keep the session open for at least 3 minutes.
Detect completion by catching the page exception when the router reboots:

```python
with page.expect_file_chooser() as fc_info:
    page.click('.file-button')
fc_info.value.set_files('/path/to/firmware.bin')
time.sleep(2)
page.click('#t_upgrade')

start = time.time()
while time.time() - start < 240:
    try:
        page.screenshot(path='/tmp/fw_progress.png')
        time.sleep(15)
    except Exception:
        print('Router rebooting — flash complete')
        break
```

### Firmware source (AU)
Download from: `https://www.tp-link.com/au/support/download/archer-vr1600v/v2/`
Extract zip then upload the `.bin`. The zip may have a header-offset warning — `unzip -o`
still extracts correctly (exit 1 is harmless).

## TP-Link Archer VR1600v — UI mechanics (tp-select, button-groups, IP octets)

The VR1600v uses a **different widget library** from the AX55. Patterns below were confirmed against Build 260317 (re-check after firmware upgrade).

### Dropdown: tp-select (NOT su-select)

The VR1600v uses `.tp-select` divs with `.select-box` inside and a floating `<li>` list.
`page.select_option()` and `.su-select` patterns from the AX55 DO NOT work.

Working pattern — open by clicking the `.select-box`, then click the option `<li>` by coordinate:

```python
# 1. Click the dropdown to open it
page.mouse.click(760, channel_y)   # x=~760 is centre of the select box
time.sleep(1.5)

# 2. Find the option <li> by text, get its position
opt_pos = page.evaluate('''
    () => {
        const lis = document.querySelectorAll('li');
        for (let li of lis) {
            if (li.offsetParent && li.innerText.trim() === '6') {
                const r = li.getBoundingClientRect();
                return {x: r.x + r.width/2, y: r.y + r.height/2};
            }
        }
        return null;
    }
''')
if opt_pos:
    page.mouse.click(opt_pos['x'], opt_pos['y'])
    time.sleep(1)
```

**Y coordinates for 2.4GHz wireless settings page (1280x800):**
| Control | Y |
|---|---|
| Channel dropdown | 435 |
| Channel Width dropdown | 471 |
| Transmit Power dropdown | ~507 |

After opening channel dropdown, options appear at x≈677, starting at y≈472 (Auto), 508 (ch1), 544 (ch2), ..., 688 (ch6), etc. (36px per step).

### Button-group toggles (DoS, Firewall)

TP-Link's On/Off toggles are `<button id="enableDoSProtectionOn">` wrapped in
`<ul class="button-group-cover">` which intercepts pointer events — `page.click('#id')` will
timeout. Use JavaScript dispatch:

```python
page.evaluate('''
    () => {
        const btn = document.getElementById('enableDoSProtectionOn');
        if (btn) btn.dispatchEvent(new MouseEvent('click', {bubbles: true}));
    }
''')
time.sleep(2)
# Verify: check className — 'selected' means active
state = page.evaluate("() => document.getElementById('enableDoSProtectionOn')?.className")
print('DoS enabled:', 'selected' in (state or ''))
```

Button IDs follow the pattern: `enable<Feature>On` / `enable<Feature>Off`
- DoS: `enableDoSProtectionOn` / `enableDoSProtectionOff`
- IPv4 SPI: `enableFirewallV4On` / `enableFirewallV4Off`
- IPv6 SPI: `enableFirewallV6On` / `enableFirewallV6Off`

### DNS / IP address fields (octet-split inputs)

IP address fields are split into 4 separate `<input>` elements with no IDs. Locate by
Y coordinate — primary and secondary DNS rows are at fixed Y positions on the LAN page.

```python
# After navigating to Advanced > Network > LAN Settings:
# Find all visible text inputs, group by Y coordinate
inputs = page.evaluate('''
    () => {
        return Array.from(document.querySelectorAll('input[type="text"]'))
            .filter(i => i.offsetParent !== null)
            .map(i => ({id: i.id, value: i.value,
                        y: Math.round(i.getBoundingClientRect().y)}));
    }
''')
# DNS rows appear at the two Y values with value '0' in all 4 octets:
# Primary DNS: y≈639, Secondary DNS: y≈676 (may vary by firmware)
dns_groups = {}  # group by y
for inp in inputs:
    dns_groups.setdefault(inp['y'], []).append(inp)

# Set octets: fill '1','1','1','1' for 1.1.1.1
octet_map = {'1.1.1.1': ['1','1','1','1'], '1.0.0.1': ['1','0','0','1']}
# Then page.fill_nth() or evaluate to set values directly
```

Alternatively — set all 4 octets via JS:
```python
def set_ip_row(page, row_y, octets, tolerance=15):
    page.evaluate(f'''
        (args) => {{
            const [y, octs, tol] = args;
            const inputs = Array.from(document.querySelectorAll('input[type="text"]'))
                .filter(i => i.offsetParent !== null)
                .filter(i => Math.abs(i.getBoundingClientRect().y - y) < tol)
                .sort((a,b) => a.getBoundingClientRect().x - b.getBoundingClientRect().x);
            octs.forEach((val, idx) => {{
                if (inputs[idx]) {{
                    inputs[idx].value = val;
                    inputs[idx].dispatchEvent(new Event('input', {{bubbles:true}}));
                    inputs[idx].dispatchEvent(new Event('change', {{bubbles:true}}));
                }}
            }});
        }}
    ''', [row_y, octets, tolerance])
```

### Admin password form field IDs

The Administration page uses `curName`/`newName` (NOT `curUser`/`newUser`):
```python
page.fill('#curName', 'admin')    # Old username
page.fill('#curPwd', 'admin')     # Old password
page.fill('#newName', 'admin')    # New username (must not be blank)
page.fill('#newPwd', NEW_PW)      # New password
page.fill('#cfmPwd', NEW_PW)      # Confirm password
```
Error code 84602 = "New Username cannot be blank" — always fill `newName`.

### Post-save verification on VR1600v

After saving wireless settings, read back the dropdown value:
```python
ch_val = page.evaluate("() => document.querySelector('#_channel .select-box')?.innerText?.trim()")
w_val = page.evaluate("() => document.querySelector('#_chnwidth .select-box')?.innerText?.trim()")
```
Dropdown IDs follow `#_<field>` pattern: `#_channel`, `#_chnwidth`, `#_mode`, `#_sec`.

### Settings audit checklist (VR1600v)

When auditing a new VR1600v unit, check and fix in order:
1. **DNS (DHCP)** — default is 0.0.0.0/0.0.0.0 (broken); set 1.1.1.1 / 1.0.0.1
2. **2.4GHz channel** — default Auto; pin to ch1 or ch6 based on neighbourhood scan
3. **2.4GHz width** — default Auto; set 20MHz for better range/stability
4. **DoS Protection** — default disabled; enable it
5. **WPS** — disable if not actively used (Advanced > Wireless > Advanced Settings toggle)
6. **NTP Server II** — default 0.0.0.0; add `time.cloudflare.com`
7. **Admin password** — default `admin`; change immediately
8. **DST** — check timezone for that unit's locale (this-household AU: GMT+10 Brisbane; DST ~Oct). Do not assume AU timezone on other VR1600v units.

## Telstra Smart Modem Gen 2 (Arcadyan LH1000)

This is the ISP-provided gateway at 192.168.0.1 on this household network. It sits upstream of the AX55, which is connected downstream as an access point/router.

### Key facts
- Gateway IP: 192.168.0.1
- Model: Arcadyan LH1000 (branded Telstra Smart Modem Gen 2)
- Serial: ARC1916508905, Firmware: 0.20.04r
- Admin credentials: username `admin`, password is household-specific (not 'Allemo094' — that's the AX55; try 'Telstra' or the label on the device)
- The AX55 is NOT at 192.168.0.1 on this network — do not confuse them.

### Login pattern
The LH1000 login page (`http://192.168.0.1/login.htm`) is NOT a simple form POST — it runs JavaScript encoding before submitting. jQuery's `$J(function(){...})` DOMready handler auto-fills `admin/Telstra` when `credentials_update_flag=0`, but **this flag does not indicate the real current password** — it is only a UI hint. The login submits credentials encoded by `do_encode(pw, true)` which calls `ArcSHA512(ArcMD5(pw))` — SHA-512 of the MD5 hash — plus a time-based `httoken` from `ArcBase._t()` via the page's own `login()` function.

**Correct Playwright approach:**

```python
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
    page = browser.new_page(viewport={'width': 1440, 'height': 900})  # must be >900px wide for 'Normal' view
    page.goto('http://192.168.0.1/login.htm', wait_until='networkidle')  # not 'load' — waits for async CGI calls
    time.sleep(8)  # let jQuery DOMready handler auto-fill fields first
    # Override auto-filled password AFTER jQuery runs
    page.evaluate(f'document.getElementById("passwordNormal").value = "{PASSWORD}"')
    time.sleep(0.3)
    page.evaluate('login()')  # call the page's own login() — handles encoding + httoken
    time.sleep(10)
    if 'err=1' in page.url or 'login' in page.url.lower():
        lock = page.evaluate('() => loginFail_lock')
        print(f'LOGIN FAILED — lockout: {lock}s')
```

Verify `ArcBase` and `$J` loaded before calling `login()`:
```python
assert page.evaluate("() => typeof ArcBase !== 'undefined'"), "ArcBase not ready"
```

**Remote access via SSH SOCKS5 proxy:** When the router is on a remote LAN (e.g. Natasha's), route Playwright through a SOCKS5 proxy on the remote machine. Do NOT use `-L` port-forwarding — the LH1000 makes async CGI calls (`cgi_login.js`, `cgi_get_led_rear.js`) to various sub-paths during page load; a single `-L 18001:192.168.0.1:80` tunnel silently drops those calls, breaking ArcBase/jQuery initialization so the `login()` function is never defined. SOCKS5 routes ALL TCP transparently:

```bash
ssh -f -N -D 20000 Administrator@<tailscale_ip>
```

```python
browser = p.chromium.launch(
    headless=True,
    proxy={"server": "socks5://127.0.0.1:20000"},
    args=["--ignore-certificate-errors"]
)
```

The SOCKS5 proxy makes all TCP originate from the remote machine's LAN IP. Lockout from multiple failed attempts will lock THAT machine's IP out of the router — read `loginFail_lock` and wait between attempts.

### Navigation structure (post-login)
- Device list: `http://192.168.0.1/owl_lan_device.htm?m=basic`
- Per-device detail: `http://192.168.0.1/client.htm?clientip=192.168.0.X&m=basic`
- Broadband: `http://192.168.0.1/broadband.htm?m=basic`
- Wi-Fi: `http://192.168.0.1/wifi24.htm?m=basic`
- Standard anchor links in nav bar — not hash routes.

### DHCP device list — what's on this network
See `references/telstra-modem-device-map.md` for the current device inventory (IPs, MACs, hostnames, device notes).

### Pitfalls (LH1000)
- **Do NOT use `keyboard.press('Enter')` or button selectors to submit.** Use `page.evaluate('login()')` — the `login()` function does encoding before form submit; Enter can fire before jQuery initializes.
- **`credentials_update_flag=0` is NOT a password indicator.** It means the login page auto-fills `admin/Telstra` as a UI hint. The actual password may be different. Never assume the password is 'Telstra' because this flag is 0.
- **`wait_until='networkidle'` is required** (not `'load'` or `'domcontentloaded'`). The page makes async CGI calls (`cgi_login.js`, `cgi_get_led_rear.js`) that must complete for `ArcBase` and `$J` to initialize. An SSH `-L` tunnel that covers only port 80 silently drops these side-path calls and ArcBase never loads — use SOCKS5 (`-D`) instead.
- **Wait 8s after `networkidle`** before touching fields — jQuery's DOMready auto-fill runs after the page settles and overwrites fields you set earlier.
- **Viewport width must be >900px.** Narrow viewports use a different DOM layout ('Small' view) with `usernameSmall`/`passwordSmall` IDs. Use 1440px width for 'Normal' view.
- **IP-based lockout, not session-based.** After ~3 failures, `loginFail_lock` is set in the page JS. Read it with `int(page.evaluate('() => loginFail_lock'))` to get lockout seconds remaining. When using SOCKS5, the locked IP is the remote machine's LAN IP, not your Tailscale IP.
- **WPS form.submit() side effects:** form.submit() on wifi24.htm or wifi5.htm saves ALL form fields, not just WPS. Verify no password fields are accidentally populated before submitting.
- **`err=1` in redirect URL** means wrong password. Do not retry silently.
- **Do NOT use `page.fill()` on the LH1000 password field.** The password input's value is read by `do_encode()` via direct DOM `.value` access after jQuery auto-fills it. `page.fill()` clears and retypes but does NOT trigger the Vue/jQuery value setter that `do_encode()` needs. Use `page.evaluate(f'document.getElementById("passwordNormal").value = "{PASSWORD}"')` to set the value directly, then call `page.evaluate('login()')`.
- **Do NOT attempt raw POST to `login.cgi`.** The login requires `ArcSHA512(ArcMD5(pw))` encoding PLUS a time-based `httoken` from `ArcBase._t()` — both generated client-side.
- **Password change field layout varies.** Use `page.evaluate("() => Array.from(document.querySelectorAll('input[type=\"password\"]')).length")` to count password fields before filling. Populate by position index.
- **Verify password change in a fresh browser.** Confirm the new password works before closing the session — do NOT test the old password first (consumes lockout budget).
- The 192.168.0.1 gateway on this household network is the Telstra modem, NOT the AX55. Confirm by checking the page title before automating.
- This household modem admin password is `Gunn1967` (changed from the factory default). See `references/telstra-modem-device-map.md` for the full credential state.

### LH1000 security hardening checklist
When auditing/hardening this modem, check in order:
1. **Firewall** (`/wan_firewall.htm?m=adv`): DoS=On (`fw_dos_enable`), WAN ping=Off (`fw_ping_enable`), DMZ=Off (`dmz_enable`)
2. **Remote management** (`/remote_management.htm?m=adv`): Off (`rmtmgmt_enable`)
3. **WPS 2.4GHz** (`/wifi24.htm?m=adv`): Off — checkbox `name="wps_enabled"`
4. **WPS 5GHz** (`/wifi5.htm?m=adv`): Off — same field name
5. **Admin password** (`/user.htm?m=adv`): not factory default
6. **Firmware** (visible on login page without auth as `runtime_code_version`): `0.20.04r` as of Sep 2026

## Brother MFC-L2800DW — web UI automation

The Brother web UI requires a **password-only** login (no username field). The admin area is gated behind HTTPS. The firmware update flow is a two-step check-then-update cycle.

### Login
```python
# Navigate to status page first (shows Login button in sidebar)
page.goto('https://192.168.0.5/home/status.html', wait_until='domcontentloaded')
time.sleep(4)
# Password field: input name='Bcaa', id='LogBox'
# Submit: input id='login' (type=submit)
page.query_selector('input#LogBox').fill(PASSWORD)
page.click('input#login')
time.sleep(4)
# Verify: URL should not contain 'passerror'
```

### Firmware check and update
```python
page.goto('https://192.168.0.5/admin/firmwareupdate.html', wait_until='domcontentloaded')
time.sleep(4)

# Step 1: check for new firmware (id='forupdate'; not a standard button — use evaluate)
page.evaluate("document.getElementById('forupdate').click()")
time.sleep(15)  # server contacts Brother update server; must wait

# Step 2: if update available, the page shows 'New Firmware Version' text and an Update button
# The Update button has onclick='update_submit()' — click by bounding box, not by selector
page.on('dialog', lambda d: d.accept())  # accept any confirm() dialogs
update_btn = page.query_selector("input[value='Update'], button:has-text('Update')")
if update_btn:
    box = update_btn.bounding_box()
    page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
    time.sleep(5)
    # Page navigates to ?pc=2 and shows 'Updating the firmware. Do not switch the machine off.'
    # Printer then goes offline for ~45 seconds while flashing

# Step 3: wait for printer to come back
import subprocess, time
for _ in range(30):
    time.sleep(5)
    r = subprocess.run(['curl','-sk','--max-time','3','-o','/dev/null','-w','%{http_code}',
                        'https://192.168.0.5/'], capture_output=True, text=True)
    if r.stdout != '000':
        break
```

### Pitfalls (Brother web UI)
- `page.click('button#forupdate')` times out — the check button requires `page.evaluate("document.getElementById('forupdate').click()")` instead.
- The firmware check requires ~15s to contact Brother's update server; clicking Update before the check completes has no effect.
- A printer that comes back online in under 10 seconds has NOT flashed — the actual flash takes ~45s offline. If it comes back immediately, the check ran but the Update click did not fire; retry the click.
- The firmware update confirmation page URL is `?pc=2` and the body contains 'Updating the firmware'. If the URL is still `?pc=-1` after the click, the click missed.
- Verify firmware version post-update by logging in again and reading `/general/information.html` — `page.inner_text('body')` on that page contains 'Main Firmware Version' followed by the version string. Do not trust the pre-update cached page.
- The Brother web UI enforces a session timeout — if the check takes >15s and the session expired, the update button will be missing; re-login before the update step.
- Firmware version is visible without login at `/general/information.html?kind=item` after logging in — not from the unauthenticated status page.
- `page.click('input#login')` fires correctly; if the URL redirects to `/etc/passerror.html`, the password is wrong.
- TLS settings: the printer supports TLS 1.2 and 1.3 (check `/network/ssl.html` if auditing TLS config).

## Asus router contrast

Asus routers (RT-AX55, etc.) use `/cgi-bin/luci/` endpoints with a stok token in the URL path. Asus-specific API notes live in the `linux-wifi-stability` skill (its `asus-router-hardening.md`) — that file is **not** in this skill's `references/`.

## References
- `references/tplink-ax55-device-state.md` — this-router-only live AX55 state (firmware, HTTPS-only, CGNAT, NextDNS, DHCP/MAC). Re-read; do not copy IDs/IPs from memory.
- `references/tplink-vr1600v.md` — VR1600v session detail (different LAN default 192.168.1.1)
