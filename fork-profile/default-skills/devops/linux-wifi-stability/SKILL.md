---
name: linux-wifi-stability
triggers:
  - Wi-Fi is dropping intermittently or showing high latency on a Linux desktop
  - NetworkManager shows connection errors or random disconnects
  - Kernel journal shows Wi-Fi driver errors or firmware reload events
  - Diagnosing and mitigating Wi-Fi instability on Linux using NetworkManager and kernel evidence
  - WiFi optimization: retries, throughput, band steering, PMF, modprobe tuning on Linux
  - NIC stuck on 2.4 GHz despite supporting 5 GHz
  - Installing Ralink/MediaTek WiFi firmware on Ubuntu or Lubuntu
  - rfkill hard block on Linux laptop
  - WPA2+WPA3 mixed mode nmcli connection failure
  - Setting up persistent SSH remote access to a Linux laptop that moves between networks
  - Installing Tailscale on Ubuntu/Lubuntu for mesh VPN remote access
  - Enabling remote sudo over SSH without interactive password prompts
description: >
  Use when diagnosing and mitigate intermittent Wi-Fi instability on Linux desktops using NetworkManager, kernel/journal evidence, and reversible per-SSID fixes before escalating to router or driver changes.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [wifi, networkmanager, linux, troubleshooting, iwlwifi, verification]
    related_skills: [verification-before-completion, wayland-session-management]
related_skills:
  - hermes-agent
  - atomic-desktop-app-installation
  - verification-before-completion
  - wayland-session-management
---

# Linux Wi-Fi Stability

Use this when the user reports unstable Wi-Fi on a Linux desktop or laptop: drops, roaming loops, intermittent latency, repeated reconnects, beacon-loss messages, DHCP churn after association, or a connection that appears associated but behaves unreliably.

This skill is for live diagnosis on the current machine. Prefer reversible per-connection changes first. Avoid system-wide driver tweaks until logs show a strong reason.

## Goals

- Confirm whether the problem is real and local
- Separate RF/AP instability from DNS/application problems
- Apply the narrowest safe fix first
- Verify with fresh journal/link evidence before claiming improvement

## Fast workflow

1. Inspect current NetworkManager and Wi-Fi state.
2. Inspect kernel + NetworkManager logs for disconnect reasons.
3. Inspect live link quality and station counters.
4. If evidence suggests client/AP instability, apply per-SSID stability tweaks first:
   - disable Wi-Fi powersave for that connection
   - force permanent MAC on that connection
   - disable MAC randomization for that connection
5. Reconnect.
6. Verify no fresh beacon-loss/disconnect events over a short observation window.
7. If instability persists, escalate to band/AP/driver-specific mitigation.

## Core evidence to gather

### Current state
Use NetworkManager to identify:
- interface name
- active SSID/BSSID
- band/channel/frequency
- signal level
- whether the device is actually connected

Useful checks:
- `nmcli device status`
- `nmcli dev wifi list`
- `nmcli connection show --active`
- `nmcli connection show '<SSID>'`
- `iw dev`
- `iw dev <ifname> link`
- `iw dev <ifname> station dump`
- `ip -brief addr`
- `rfkill list`

### Logs
Look for patterns, not isolated lines.

Key signals:
- `CTRL-EVENT-BEACON-LOSS`
- `missed beacons exceeds threshold`
- `Connection to AP ... lost`
- `deauthenticated`
- repeated `ssid-not-found`
- rapid disconnect/reconnect loops
- DHCP restarts that are secondary to link loss

Primary sources:
- `journalctl -b -u NetworkManager --no-pager`
- `journalctl -b -k --no-pager | grep -Ei 'wlan|wifi|iwl|ath|brcm|mt7|rtw|disconnect|deauth|roam|firmware|beacon|txpower'`

The `txpower` keyword catches AP-advertised TX power limits: a line like
`wlp0s20f3: Limiting TX power to 0 (-128 - 0) dBm as advertised by <BSSID>`
is a distinct failure mode — the adapter's transmit power is being suppressed by the AP's country/regulatory IE. This appears once at association time and is easy to miss without the keyword.

## First safe fix: per-SSID stability profile

When logs show beacon loss, disconnect loops, or suspicious AP behavior, try these connection-local settings before deeper changes:

- `802-11-wireless.powersave 2`  → disable powersave
- `802-11-wireless.cloned-mac-address permanent`
- `802-11-wireless.mac-address-randomization never`

Example:

```bash
nmcli connection modify "$SSID" \
  802-11-wireless.powersave 2 \
  802-11-wireless.cloned-mac-address permanent \
  802-11-wireless.mac-address-randomization never
nmcli connection down "$SSID" || true
nmcli connection up "$SSID"
```

Why this helps:
- Some APs behave poorly with client powersave on marginal links.
- Some APs handle randomized or stable-SSID MAC behavior badly across reconnects.
- Applying this per SSID is safer than changing global defaults.

## Verification requirements

Never claim the fix worked just because reconnection succeeded.

Verify with:
- `iw dev <ifname> link`
- `iw dev <ifname> station dump`
- `journalctl --since '-2 minutes' ...`
- NetworkManager connection summary showing connected state and gateway/IP

Positive signs:
- still associated after the reconnect window
- `beacon loss: 0` or no increasing loss in station dump
- no fresh `CTRL-EVENT-BEACON-LOSS`, `Connection to AP lost`, or repeated disconnect lines in the journal during observation
- stable connected state in `nmcli`/`device show`
- a clean reconnect sequence where any immediate disconnect/deactivating lines are clearly user-requested bounce events from the profile change, followed by normal activation and lease acquisition

## Escalation path if first fix is insufficient

Escalate in this order:

1. Prefer 5 GHz or 6 GHz SSID if available.
2. If the router combines bands under one SSID, test with separate SSIDs.
3. Check for crowded 2.4 GHz conditions and poor channel choice.
4. Try a different BSSID/AP if there are multiple nodes under the same SSID.
5. Apply iwlwifi/iwlmvm modprobe power parameters (see below).
6. Only then consider stronger adapter/driver workarounds.

### Why the NIC appears "stuck" on 2.4 GHz

NM does not steer bands — it associates with the best visible BSSID for the SSID.
If the router's 5 GHz radio is off or broadcasting a different SSID, there is no
5 GHz BSSID to choose. Verify with `nmcli dev wifi list` and look for the router's
BSSID on a 5 GHz channel (channels 36+ or 149+). If absent, the fix is router-side
(enable 5 GHz radio), not client-side.

Once a 5 GHz BSSID is visible, force NM to prefer it:

```bash
# Create a 5 GHz-only NM profile (band "a" = 5 GHz/VHT/HE only)
nmcli connection add type wifi ssid "MySSID" \
  con-name "MySSID-5G" \
  802-11-wireless.band "a" \
  802-11-wireless.powersave 2 \
  connection.autoconnect-priority 10

nmcli connection modify "MySSID-5G" \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.psk "PASSWORD"

# Lower 2.4 GHz profile priority so 5G wins when available
nmcli connection modify "MySSID" connection.autoconnect-priority 0
```

To pin to a specific 5 GHz BSSID (most reliable):
`802-11-wireless.bssid "XX:XX:XX:XX:XX:XX"`

### Channel width: 20 MHz vs 40 MHz on 2.4 GHz

In dense neighborhoods: **keep 20 MHz**. Do NOT enable 40 MHz on 2.4 GHz when
multiple APs are visible on adjacent channels. Reasons:
- 40 MHz at center ch 1 spans channels 1–7, absorbing interference from neighbor
  APs on channels 2–5 that are NOT currently competing with you.
- 802.11n BSS coexistence will force a compliant router back to 20 MHz anyway when
  it detects overlapping BSSes.
- Each channel-width doubling adds ~3 dB of noise floor (doubled noise bandwidth).
On 5 GHz, 80 MHz is generally safe on UNII-1 (36/40/44/48) or UNII-3 (149–161).

### TX retry rate: interpreting and fixing elevated retries

Elevated retry rate (~8%+ from `iw station dump`) is usually caused by:
1. Co-channel interference — multiple APs on the same channel
2. iwlmvm power_scheme=2 (balanced) — MVM firmware power logic introduces timing gaps
3. Rate adaptation mismatch — MCS too high for actual SNR, retries before drop
4. Bluetooth coexistence — AX201 shares antenna complex with BT (`rfkill block bluetooth`)

Check retry rate:
```bash
iw dev <ifname> station dump | grep -E "(retries|tx packets)"
```
Target: <5% (< ~5000 retries per 100k packets).

### iwlwifi/iwlmvm modprobe parameters (Intel AX200/AX201)

Even with NM `powersave=2` (disabled), the MVM firmware's own power scheme can
introduce timing issues that inflate retries. Both layers must be set:

```
# /etc/modprobe.d/iwlwifi.conf
options iwlwifi power_save=0        # same as 'iw set power_save off'
options iwlwifi uapsd_disable=3     # disable U-APSD for BSS + P2P
options iwlmvm power_scheme=1       # always-on (1=on, 2=balanced, 3=low-power)
```

iwlmvm will override iwlwifi's power setting if only one option is set — both are
required. Apply without reboot:
```bash
sudo modprobe -r iwlmvm iwlwifi && sudo modprobe iwlwifi
cat /sys/module/iwlmvm/parameters/power_scheme   # verify: 1
```

On Fedora Silverblue, `/etc/modprobe.d/` is writable in the overlay.
DO NOT use `11n_disable=1` (kills aggregation) or `disable_11ax=true` (disables WiFi 6).
See `references/intel-ax201-optimization-deep-dive.md` for the full parameter table.

### PMF (Management Frame Protection) for WPA-PSK + WiFi 6

NM default (`pmf=0`) disables PMF. IEEE 802.11ax (WiFi 6) requires PMF for HE
connections. Without PMF, any nearby radio can forge a deauth frame and disconnect
your client — this is the basis of deauth floods and WPA handshake capture attacks.

Check current value:
```bash
nmcli connection show "MySSID" | grep pmf
# 0=default(off), 2=optional(negotiate), 3=required
```

Set to optional (safe for all WPA2 routers):
```bash
nmcli connection modify "MySSID" 802-11-wireless-security.pmf 2
nmcli connection up "MySSID"
```

Set to required if router supports it (Asus AX-series 2019+ does):
```bash
nmcli connection modify "MySSID" 802-11-wireless-security.pmf 3
```

No throughput impact — PMF only applies to management frames, not data frames.

## Interpreting common patterns

### WiFi appears broken but internet works via another interface
When a second interface (e.g. USB ethernet adapter) is active with a lower metric, all traffic routes through it — WiFi is associated and healthy but never used for outbound packets. Diagnosis:
```bash
ip route show          # look for two default routes with different metrics
ip route get 8.8.8.8   # confirms which interface wins
```
The fix depends on intent: unplug the secondary adapter (routing resolves automatically), bring down its NM connection (`nmcli connection down "Wired connection 1"`), or raise its metric (`nmcli connection modify "Wired connection 1" ipv4.route-metric 700`). Do not touch WiFi driver or config — the radio is fine.

Note: many home routers block ICMP ping on the gateway IP (192.168.0.1) — a failed `ping 192.168.0.1` does NOT indicate no connectivity. Confirm with `ping 8.8.8.8` or `ip route get 8.8.8.8` instead.

### Beacon-loss + missed-beacon warnings + reconnect loop
Most likely RF/AP/client stability issue. Start with the per-SSID powersave and MAC fixes.

### Good association but app failures only
Likely not a Wi-Fi-layer issue. Check DNS, gateway, captive portal, or upstream connectivity separately.

### DHCP churn after disconnects
Usually downstream of link loss, not the root cause. Fix the radio/link problem first.

### Signal much worse than other devices on the same AP
Classic cause: AP is advertising a TX power cap that the Linux driver honours but other devices ignore or interpret differently. Check the kernel journal for:
`<ifname>: Limiting TX power to 0 (-128 - 0) dBm as advertised by <BSSID>`
TX power at 0 dBm means the radio is effectively off. The per-SSID powersave-off + permanent-MAC fix resolves it by keeping the radio more aggressively active; the adapter re-negotiates a workable power level after reconnect. Mobile hotspots (e.g. Android Pixel hotspot) are known to advertise 0 dBm caps. See `references/ap-txpower-cap.md`.

### Link looks healthy but throughput is low compared to AP capability
Check `iw dev <ifname> station dump` for NSS count. If TX is NSS1 while RX is NSS2, the adapter is only using one spatial stream for transmit — often a symptom of the same TX power cap or powersave throttling.

## Pitfalls

- **Hard block before anything else**: if `rfkill list all` shows `Hard blocked: yes`, no software fix will work. The physical radio has no power. Check the Fn key combo (e.g. Fn+F12 — orange LED = off, white/blue = on), BIOS wireless toggle, and any physical side-switch before debugging firmware or drivers.
- **WPA2+WPA3 mixed mode**: plain `nmcli dev wifi connect` may fail with "security key mgmt property missing" when a router advertises both WPA2 and WPA3. Workaround: use `nmcli con add` with explicit `wifi-sec.key-mgmt wpa-psk`, `wifi-sec.proto rsn`, `wifi-sec.pairwise ccmp`, and `802-11-wireless-security.pmf disable` to force WPA2 only. This also works around WPA3 negotiation issues on older drivers (e.g. rt2800pci).
- Do not jump straight to global config or module parameters when a per-connection fix can isolate the problem.
- Do not confuse router ICMP blocking with no connectivity; some gateways ignore pings.
- Do not treat a successful reconnect as proof of stability.
- Do not over-interpret a single `deauthenticated` line without surrounding journal context.
- On crowded 2.4 GHz, acceptable signal does not rule out channel contention or beacon loss.
- When the user says "signal is worse than my other devices", do NOT assume RF attenuation or antenna damage. Check the kernel journal for `txpower` first — an AP-advertised TX power cap at 0 dBm is a hard ceiling that looks identical to poor signal but is entirely fixable in software.
- After fixing one SSID (e.g. a Pixel hotspot), always confirm the user is on their intended AP before claiming the job is done. The fix from one SSID does not carry over diagnostically to another.

## Router channel change via API (TP-Link Archer / AX series)

When 2.4 GHz signal is acceptable but competing with neighbours on the same channel, changing the router channel is the next step. Use this when you can confirm:
- `nmcli dev wifi list` shows multiple APs on the same channel as the user's SSID
- The user's router is a TP-Link Archer/AX model (BSSID OUI `A8:42:A1` or `C0:25:A2` / similar TP-Link ranges)
- You have the router admin password

**Verified working approach (TP-Link Archer AX55, firmware 1.11.0):**

```bash
pip3 install tplinkrouterc6u
```

```python
from tplinkrouterc6u import TplinkRouterProvider, Connection

r = TplinkRouterProvider.get_client('http://192.168.0.1', 'ADMIN_PASSWORD')
r.authorize()

# Read current 2.4GHz config — capture ALL fields
config = r.request("admin/wireless?form=wireless_2g", "operation=read")
print(config)  # check current channel

# Write — must send full config, not just the changed field
# Partial writes (channel= only) are silently ignored on AX firmware
full_data = (
    "operation=write"
    "&enable=on"
    "&ssid=" + config['ssid'] +
    "&hidden=" + config['hidden'] +
    "&encryption=" + config['encryption'] +
    "&psk_version=" + config['psk_version'] +
    "&psk_cipher=" + config['psk_cipher'] +
    "&psk_key=" + config['psk_key'] +
    "&hwmode=" + config['hwmode'] +
    "&htmode=" + config['htmode'] +
    "&channel=6"         # target channel: 1 or 6 (avoid 11 — overlaps many neighbours)
    "&txpower=" + config['txpower'] +
    "&mu_mimo=" + config['mu_mimo'] +
    "&airtime_fairness=" + config['airtime_fairness']
)
result = r.request("admin/wireless?form=wireless_2g", full_data)
print("New channel:", result.get('channel'))
# Router will bounce radio — connection drops briefly then reconnects
r.logout()
```

Verify with `iw dev <ifname> link` after reconnect — `freq: 2412` = ch1, `freq: 2437` = ch6.

**Pitfalls:**
- The library's `set_wifi(Connection.HOST_2G, channel=N)` sends only `wireless_2g_channel=N`, which AX firmware silently treats as a read. Always use the full `r.request()` with all fields.
- The router bounces (brief radio restart) on channel change — expect "No route to host" on the read-back immediately after the write. This is expected; wait 5–10 s and reconnect.
- AX55 responses are AES-encrypted — raw `curl` cannot decrypt them. Use the library's `request()` method for all API calls.
- 5 GHz disable state: always read `r.get_status().wifi_5g_enable` first if the user has not confirmed whether 5 GHz should be touched.

See `references/tplink-ax55-api.md` for full OUI list and API notes.

For TP-Link VDSL/ADSL modem-routers (Archer VR1600v, etc.) the AX firmware API is not available. Use the `router-admin-automation` skill with Playwright instead — it has the VR1600v UI mechanics, tp-select dropdown patterns, and a settings audit checklist for that model family.

**Best practice: coordinate both sides.** When fixing channel congestion, pin the channel at the router AND set `802-11-wireless.band` in the NM profile on the client. Client-only changes still roam to the AP's chosen channel; router-only changes still depend on the client not over-riding via band steering. Doing both is the only reliable fix.

## LAN device identification (for follow-up device diagnostics)

When the user asks about a specific device on their network (TV, console, phone), identify it from the router or via network scanning before attempting to probe it.

### Workflow

1. Python threaded ping sweep to find live IPs (faster than sequential, no nmap needed):

```python
import socket, concurrent.futures, subprocess

def ping(ip):
    r = subprocess.run(['ping','-c1','-W1', ip], capture_output=True)
    return ip if r.returncode == 0 else None

with concurrent.futures.ThreadPoolExecutor(max_workers=64) as ex:
    live = [ip for ip in ex.map(ping, [f'192.168.0.{i}' for i in range(1,255)]) if ip]
print(sorted(live, key=lambda x: int(x.split('.')[-1])))
```

2. Get MAC addresses from ARP cache:
```bash
ip neigh show | grep REACHABLE
```

3. Look up manufacturer by OUI (first 6 hex digits of MAC) via `macvendorlookup.com`:

```python
from hermes_tools import web_extract
ouis = ["442745", "6490C1", "2C9E00"]   # uppercase, no colons
urls = [f"https://www.macvendorlookup.com/api/v2/{o}" for o in ouis]
result = web_extract(urls)
for r in result["results"]:
    print(r["url"], r["content"][:200])
```

Common OUI prefixes encountered:
- `A8:42:A1` → Asus (router) — NOTE: this OUI also appears in some TP-Link reference tables; always verify via macvendorlookup.com
- `44:27:45` → LG Innotek (LG TV)
- `64:90:C1` → Xiaomi
- `2C:9E:00` → Sony Interactive Entertainment (PlayStation)
- `28:95:29` → Intel Corporate (laptop wifi cards)

### LG WebOS TV probing

Once the TV is identified, check open ports:
- 3001 — WebOS SSAP WebSocket over TLS (wss://) — **correct pairing port**
- 3000 — WebOS SSAP plain WebSocket — resets connections on WebOS 24, do NOT use first
- 8008 — Google Cast / Chromecast endpoint
- 36866 — LG Connect API (HTTP, basic probe only)
- 8443 — Cast over TLS

Quick port check:
```python
import socket, concurrent.futures
tv = '192.168.0.X'
ports = [80, 3000, 3001, 8008, 8443, 36866]
def check(p):
    try:
        s = socket.socket(); s.settimeout(1); s.connect((tv, p)); s.close(); return p, True
    except: return p, False
with concurrent.futures.ThreadPoolExecutor() as ex:
    open_ports = [p for p, up in ex.map(check, ports) if up]
```

**Pairing:** use wss://TV_IP:3001 with ssl verify disabled. The user must accept a prompt on the TV screen. Save the returned `client-key` for future sessions (no re-prompt needed).

**Critical SSAP limitation on WebOS 24:** WiFi signal strength, SSID, IP, DNS config, and firmware version are NOT accessible via the SSAP second-screen API — these require privileged luna service access. Probing these URIs returns `{}` silently, not an error. Use `ping -c 10 <TV_IP>` as a WiFi health proxy instead (avg > 5ms or high mdev = instability). See `references/lg-webos-api.md` for full API capability table and working pairing code.

**Quick non-API wins for LG TV connectivity issues (in order of impact):**
1. Settings → General → Quick Start+: ON — keeps WiFi radio active during standby, most impactful fix
2. Settings → Support → Software Update → Check for Updates — WiFi fixes ship in firmware
3. Settings → Connection → Network → Advanced WiFi Settings → DNS: set to 1.1.1.1

### PlayStation 5 WiFi diagnostics

OUI: `2C:9E:00` → Sony Interactive Entertainment

**Rest mode limitation:** PS5 in rest mode closes all ports. Port scanning returns nothing open — this is normal, not a connectivity problem. Wake the PS5 first if you need to probe it.

**Ping as health proxy** (same as TV — use when no ports are open):
```bash
ping -c 20 -i 0.2 192.168.0.X
```
Healthy: avg < 5ms, mdev < 3ms. Spiky avg (>15ms) with mdev > 20ms = WiFi power-save cycling or congestion.

**Manual settings to tune on the PS5 (cannot be done remotely):**

1. Settings → Network → Settings → Set Up Internet Connection → your network → Options → DNS Settings → Manual
   - Primary: 1.1.1.1, Secondary: 1.0.0.1
2. Settings → Network → Settings → MTU → set to 1473 (avoids fragmentation on PPPoE/NATted connections)
3. Settings → Saved Data and Game/App Settings → Rest Mode → "Stay Connected to the Internet" → confirm intentional setting (on = background downloads continue; off = cleaner disconnect)
4. **Ethernet** — the PS5 supports GbE and benefits most of any device from a wired connection, especially for online gaming where latency variance matters more than throughput

**NAT type:** if the user reports NAT Type 3 or strict NAT causing multiplayer issues, check router UPnP — Settings → Network → View Connection Status → NAT Type. Enable UPnP on the router if NAT Type is not 2.

## Identifying hidden SSIDs and unknown networks

`nmcli dev wifi list` shows `--` for the SSID of any AP that suppresses beacon SSIDs.
Use `iw dev <ifname> scan` to get full beacon data including OUI, capabilities, and
BSS Load — enough to fingerprint the hidden AP back to a known neighbor.

### Scan workflow (hidden SSID recon)

1. Run a full scan:
```bash
nmcli dev wifi list          # quick view; hidden SSIDs show as --
sudo iw dev wlp0s20f3 scan   # full beacon data
```

2. Extract the relevant block for a hidden BSSID (e.g. `8E:78:48:94:F0:6B`):
```bash
sudo iw dev wlp0s20f3 scan 2>/dev/null | grep -A 80 'BSS 8e:78:48'
```

3. Cross-reference the OUI (first 3 octets) against named APs in `nmcli dev wifi list`.
   A hidden AP with OUI matching a named neighbor is almost always a secondary BSSID
   (guest interface, IoT SSID, or management BSS) on the same hardware.

### Key fields to read from `iw scan` output

- `freq:` — channel/band (2412=ch1, 2437=ch6, 5200+=5GHz)
- `signal:` — dBm strength
- `RSN: Authentication suites:` — PSK=WPA2, SAE=WPA3, PSK+SAE=mixed
- `RSN: Capabilities: MFP-capable` — PMF support
- `BSS Load: station count:` — live client count on that AP
- `Country:` — regulatory domain (`bogus` = router didn't set it correctly)
- `HE capabilities:` — confirms WiFi 6
- `HT operation: primary channel:` — actual channel

### Interpreting hidden SSIDs

Hidden SSID ≠ rogue network. Most hidden SSIDs are secondary BSSIDs
(same router, different virtual interface) — OUI matches a named neighbor.
Locally-administered MAC (2nd hex digit is 2,6,A,E): bit 1 of first octet is set,
indicating a virtual/randomized address derived from the real hardware MAC.

A network warrants investigation only if: OUI matches no known device, signal
appears/disappears suspiciously, or BSS Load shows clients at unusual hours.

See `references/hidden-ssid-identification.md` for a worked example (Coppermind AP,
Aug 2026: two hidden BSSIDs traced back to neighbor router's virtual interfaces).

## Asus AX-series router hardening (WPA3, WPS, DNS, guest isolation)

Verified on Asus AX-series (OUI A8:42:A1). Admin UI at `http://192.168.0.1` or `http://router.asus.com`.

1. **WPA2/WPA3 mixed** (Wireless > Wireless Security): set both bands; do NOT use WPA2-only — WiFi 6 (HE) runs without PMF protection under WPA2-only.
   - After enabling WPA3: `nmcli connection modify "SSID" 802-11-wireless-security.key-mgmt wpa-psk; nmcli connection modify "SSID" 802-11-wireless-security.pmf 2`
   - For WPA3-only: key-mgmt=`sae`, pmf=`3`
2. **Disable WPS** (Wireless > WPS > Enable WPS: Off) — WPS PIN is brute-forceable.
3. **WAN DNS** (WAN > WAN DNS Setting): 1.1.1.1 / 1.0.0.1 — catches devices ignoring DHCP DNS.
4. **5 GHz channel bandwidth** (Wireless > General > 5 GHz): 80 or 160 MHz; channels 36 or 149 are clean in AU suburban areas.
5. **Guest network for IoT** (Guest Network): AP Isolation=On, Access Intranet=Off.
6. **IPv6 stable-privacy**: `nmcli connection modify "SSID" ipv6.addr-gen-mode stable-privacy`

Hermes sudo pattern: pre-build a script, user runs `sudo /tmp/netfix.sh` once — avoids sudo cache expiry across tool calls.

## Hidden SSID identification (locally-administered MAC detection)

`nmcli dev wifi list` shows `--` entries. Identify with `sudo iw dev <ifname> scan 2>/dev/null | grep -A 80 'BSS <bssid>'`.

Locally-administered MACs (router virtual BSSIDs for guest/IoT/hidden): bit 1 of first octet = 1.
- Example: primary `84:78:48:94:F0:6C` → hidden variants `8E:...` (2.4 GHz) and `8A:...` (5 GHz) — same router.
- Quick check: `printf '%d\n' 0x8E` → 142, `142 & 2` = 2 = locally administered.

A hidden SSID warrants real investigation only if: OUI matches no known neighbor, signal appears/disappears suspiciously, or BSS Load shows clients at unusual hours.

## When to write a reference file

Add a `references/` note when you discover adapter- or AP-specific behavior worth reusing, such as Intel AX201 + beacon-loss patterns, a vendor router quirk, or a validated escalation recipe.

Current supporting notes:
- `references/ralink-rt5390-lubuntu-setup.md` — RT5390 firmware install, rfkill hard block resolution, WPA2+WPA3 mixed-mode nmcli fix, SSH remote access setup, remote sudo via visudo NOPASSWD, Tailscale install on Ubuntu/Lubuntu and Fedora Silverblue for persistent cross-network access
- `references/intel-ax201-beacon-loss.md`
- `references/intel-ax201-optimization-deep-dive.md` — full modprobe params, PMF, 5G forcing, DNS, channel-width reasoning (live-verified on kernel 7.1.8)
- `references/ap-txpower-cap.md`
- `references/tplink-ax55-api.md`
- `references/lg-webos-api.md`
- `references/asus-router-hardening.md` — Asus AX-series hardening (WPA3, WPS-off, DNS, guest network, IPv6); OUI A8:42:A1 = Asus (not TP-Link)
- `references/hidden-ssid-identification.md` — worked example: fingerprinting hidden BSSIDs via iw scan beacon data
