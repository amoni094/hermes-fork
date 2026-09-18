# TP-Link Archer AX55 API Notes

Verified on: Archer AX55 v1, firmware 1.11.0, August 2026.

## Identification

- BSSID OUI: `A8:42:A1` (TP-Link)
- Router UI redirects to `/webpages/index.html` — Vue.js SPA
- Firmware detection: `gunzip -c /tmp/tplink-index.gz | grep -i model`
- Library auto-detects firmware and returns `TplinkRouterSG` client for SG/AX firmware

## Authentication

The AX55 uses AES-encrypted request/response payloads with HMAC-SHA256 signatures. Direct `curl` returns `{"data":""}` (encrypted). Always use the `tplinkrouterc6u` Python library.

```bash
pip3 install tplinkrouterc6u
```

```python
from tplinkrouterc6u import TplinkRouterProvider, Connection
r = TplinkRouterProvider.get_client('http://192.168.0.1', 'ADMIN_PASSWORD')
r.authorize()
# r._stok contains the session token (for debugging only)
```

## Key API endpoints (via `r.request(path, data)`)

| Endpoint | Read data | Write data |
|---|---|---|
| `admin/wireless?form=wireless_2g` | 2.4 GHz full config | See below |
| `admin/wireless?form=wireless_5g` | 5 GHz full config | Same pattern |
| `admin/system?form=logout` | — | `operation=write` |

## 2.4 GHz read response fields

```json
{
  "ssid": "MyNetwork",
  "channel": "11",
  "current_channel": "11",
  "hwmode": "bgnax",
  "htmode": "auto",
  "txpower": "high",
  "enable": "on",
  "hidden": "off",
  "encryption": "psk",
  "psk_version": "rsn",
  "psk_cipher": "aes",
  "psk_key": "<password>",
  "mu_mimo": "off",
  "airtime_fairness": "off"
}
```

## Channel change — critical gotcha

**Partial writes are silently ignored.** The router returns HTTP 200 with `{"data":""}` and appears to succeed, but the channel does not change. You must send ALL config fields in the write:

```python
config = r.request("admin/wireless?form=wireless_2g", "operation=read")

full_data = (
    "operation=write"
    "&enable=on"
    f"&ssid={config['ssid']}"
    f"&hidden={config['hidden']}"
    f"&encryption={config['encryption']}"
    f"&psk_version={config['psk_version']}"
    f"&psk_cipher={config['psk_cipher']}"
    f"&psk_key={config['psk_key']}"
    f"&hwmode={config['hwmode']}"
    f"&htmode={config['htmode']}"
    "&channel=6"           # ← changed field
    f"&txpower={config['txpower']}"
    f"&mu_mimo={config['mu_mimo']}"
    f"&airtime_fairness={config['airtime_fairness']}"
)
result = r.request("admin/wireless?form=wireless_2g", full_data)
# result['channel'] will show new value if write succeeded
```

The radio briefly restarts after channel change. Expect connection drop and "No route to host" on the next call — this is normal. Wait 5–10 s for reconnect.

## Verify success

```bash
iw dev wlp0s20f3 link | grep freq
# freq: 2412 = ch1, freq: 2437 = ch6, freq: 2462 = ch11
```

## library's set_wifi() limitation

`r.set_wifi(Connection.HOST_2G, channel=N)` sends only `operation=write&wireless_2g_channel=N`. The AX firmware ignores single-field writes and returns a read response. Use `r.request()` directly with the full payload as shown above.

## 2.4 GHz channel selection guidance

- Channel 11 is the worst choice in AU/dense suburban areas — overlaps ch9-13, commonly shared with neighbours
- Prefer channel 1 or 6 (non-overlapping in 2.4 GHz 20 MHz mode)
- Scan neighbours first: `nmcli dev wifi list` — look at CHAN column and signal bars
- Pick the channel with fewest strong neighbours (signal > -70 dBm counts as competition)
- Filter to a specific channel: `nmcli dev wifi list | awk 'NR==1 || / 1 /'`

Real example from McKinnon Rd, August 2026:
- Channel 11 (original): 144McKinnonNetwork + Mel's Hub (strong) + others → very congested
- Channel 6 (first move): BecauseFi + Coppermind both at -60 dBm → still significant competition
- Channel 1 (final): no neighbours at all → signal improved from -62 to -58 dBm immediately

Lesson: always scan channel 1 before committing to channel 6. In suburban AU, ch1 is often completely empty while ch6 has been "discovered" by router auto-select.

## DHCP lease / connected device enumeration

To see all devices the router knows about via its DHCP table:

```python
from tplinkrouterc6u import TplinkRouterProvider
r = TplinkRouterProvider.get_client('http://192.168.0.1', 'ADMIN_PASSWORD')
r.authorize()
status = r.get_status()
print("wifi clients:", status.wifi_clients_total)
# Note: get_ipv4_dhcp_leases() fails on AX55 (encrypted format mismatch)
# Use python ping sweep + ip neigh show for MAC enumeration instead
r.logout()
```

For full device discovery with MACs:

```python
import socket, concurrent.futures, subprocess

def ping(ip):
    r = subprocess.run(['ping','-c1','-W1', ip], capture_output=True)
    return ip if r.returncode == 0 else None

with concurrent.futures.ThreadPoolExecutor(max_workers=64) as ex:
    live = [ip for ip in ex.map(ping, [f'192.168.0.{i}' for i in range(1,255)]) if ip]

# Then: ip neigh show | grep REACHABLE  → gives MAC addresses
```
