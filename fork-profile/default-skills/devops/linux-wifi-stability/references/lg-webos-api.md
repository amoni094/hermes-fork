# LG WebOS TV — Network Probing & SSAP API Notes

Verified on: LG OLED55C4PSA (2024 C4), WebOS 24, August 2026.

## Identification

- OUI: `44:27:45` → LG Innotek (LG TV)
- Model confirmed via SSAP: `OLED55C4PSA.AAUQLJD`
- Open ports on a typical LG WebOS 24 TV:
  - 3000 — SSAP WebSocket (plaintext) — RESETS without pairing; do NOT attempt plain ws:// first
  - 3001 — SSAP WebSocket over TLS (wss://) — correct pairing port
  - 8008 — Google Cast / Chromecast HTTP
  - 8443 — Cast TLS
  - 36866 — LG Connect API (HTTP, returns 404 for most paths but confirms TV is up)

## Pairing flow (WebOS SSAP)

Use **port 3001 / wss://** with `ssl_verify=False`. Port 3000 (plain ws://) resets connections before the handshake completes on WebOS 24.

```python
import asyncio, json, ssl, websockets

TV = "wss://192.168.0.X:3001"

REGISTER_MSG = {
    "type": "register",
    "id": "register_0",
    "payload": {
        "forcePairing": False,
        "pairingType": "PROMPT",
        "manifest": {
            "manifestVersion": 1,
            "appVersion": "1.1",
            "signed": {
                "created": "20140509",
                "appId": "com.hermes.tv",
                "vendorId": "com.hermes",
                "localizedAppNames": {"": "Hermes"},
                "localizedVendorNames": {"": "Hermes"},
                "permissions": [
                    "TEST_SECURE","CONTROL_INPUT_TEXT","CONTROL_MOUSE_AND_KEYBOARD",
                    "READ_INSTALLED_APPS","READ_NOTIFICATIONS","SEARCH","WRITE_SETTINGS",
                    "CONTROL_POWER","READ_CURRENT_CHANNEL","READ_RUNNING_APPS",
                    "READ_UPDATE_INFO","UPDATE_FROM_REMOTE_APP","READ_TV_CURRENT_TIME"
                ],
                "serial": "2f930e2d2cfe083771b7371a577c6a30"
            },
            "permissions": [
                "LAUNCH","APP_TO_APP","CONTROL_AUDIO","CONTROL_DISPLAY",
                "CONTROL_INPUT_MEDIA_PLAYBACK","CONTROL_INPUT_TV",
                "CONTROL_POWER","READ_APP_STATUS","READ_CURRENT_CHANNEL",
                "READ_INPUT_DEVICE_LIST","READ_NETWORK_STATE","READ_RUNNING_APPS",
                "READ_TV_CHANNEL_LIST","WRITE_NOTIFICATION_TOAST",
                "READ_POWER_STATE","READ_COUNTRY_INFO"
            ],
            "signatures": [{"signatureVersion": 1,
                            "signature": "fg4ghAPjr+JELSWa9pR5L7FeCpNixqEBPBuIL59R0MpPZsBwwnJtx6sgQySSWa0iS4AzNUy4mZPgfVU"}]
        }
    }
}

async def pair_and_query():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    async with websockets.connect(TV, ssl=ctx, open_timeout=10) as ws:
        await ws.send(json.dumps(REGISTER_MSG))
        # User must accept prompt on TV screen
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
            if msg.get("type") == "registered":
                client_key = msg["payload"]["client-key"]
                print("Paired! Key:", client_key)
                break

        # Re-use key in future sessions (no prompt needed):
        # payload = {"client-key": client_key, "forcePairing": False, "pairingType": "PROMPT"}

asyncio.run(pair_and_query())
```

Save the returned `client-key` — subsequent connections using it skip the on-screen prompt.

## What SSAP CAN return on WebOS 24

| URI | Returns |
|-----|---------|
| `ssap://system/getSystemInfo` | model name, serial, DVR support |
| `ssap://audio/getVolume` | volume, mute, sound output type |
| `ssap://audio/getStatus` | same as above + caller ID |
| `ssap://com.webos.applicationManager/getForegroundAppInfo` | active app ID |
| `ssap://tv/getChannelList` | channel list (empty if no antenna) |
| `ssap://com.webos.service.connectionmanager/getinfo` | MAC addresses (wifi + wired + p2p) |
| `ssap://api/getServiceList` | list of available SSAP service names |

## What SSAP CANNOT return on WebOS 24

These URIs return `{}` (empty payload) — **not an error, just no data**:

- `ssap://com.webos.service.connectionmanager/getStatus` — WiFi SSID, signal strength, IP
- `ssap://com.webos.service.connectionmanager/wifi/getStatus` — same
- `ssap://com.webos.service.network/getNetworkState` — network state
- `ssap://com.webos.service.update/getCurrentSWInformation` — firmware version
- `ssap://settings/getSystemSettings` — all system settings
- `ssap://com.webos.service.wifi/getStatus` — wifi radio status
- `ssap://com.webos.service.wifi/getNetworks` — nearby networks

These require **privileged luna service access** which is not available via the second-screen SSAP pairing tier.

**Implication:** You cannot remotely read the TV's WiFi signal strength, SSID, IP, DNS config, or firmware version via the API. All of these must be read from the router side or checked manually on the TV.

## WiFi health proxy when SSAP stats are unavailable

Use ping latency from a device on the same subnet as a proxy for WiFi stability:

```bash
ping -c 10 -i 0.2 <TV_IP>
```

Interpretation:
- avg < 5ms, mdev < 2ms → healthy WiFi link
- avg 5–15ms, mdev > 5ms → marginal, likely power-save or interference
- avg > 15ms or packet loss → real instability

Example (LG OLED55C4PSA before fixes): avg 14.9ms, min 2.7ms, max 33.8ms → marginal, power-save cycling.
After Quick Start+ on + Live Plus off: avg 7ms, max 28ms — significantly improved, remaining variance is normal WebOS background activity.

## TV-side fixes (manual, cannot be done via API)

In order of impact for intermittent connectivity issues:

1. **Quick Start+** (Settings → General → Quick Start+: ON)
   - Keeps WiFi radio active during standby
   - Eliminates reconnect delays and the drop-then-reconnect pattern
   - Most impactful fix for "TV takes forever to connect" or buffering after standby

2. **Firmware update** (Settings → Support → Software Update → Check for Updates)
   - LG C4 latest as of Aug 2026: 33.22.75 (webOS 25 also rolling out to C4)
   - WiFi stability fixes are commonly included in firmware updates

3. **DNS override** (Settings → Connection → Network → Advanced WiFi Settings)
   - Default LG DNS is slow; set to 1.1.1.1
   - Fixes buffering/loading delays that present as WiFi issues but are actually DNS latency

4. **Live Plus / ACR off** (Settings → All Settings → General → Additional Settings → Live Plus: OFF)
   - LG's Automatic Content Recognition runs continuously, fingerprinting on-screen content for ad targeting
   - Generates constant background WiFi traffic and CPU load — observable as latency spikes in ping (high mdev) even when the link itself is healthy
   - After disabling: avg ping latency to TV dropped from ~14.9ms to ~7ms in testing on LG OLED55C4PSA
   - Safe to turn off; does not affect any streaming or smart TV functionality

5. **Signal check** (Settings → Connection → Network → WiFi Connection)
   - Check signal bars while in the menu — if under 2 bars, physical placement is the issue

## Channel change impact

Router-level channel changes (see `references/tplink-ax55-api.md`) apply to all devices including the TV. No TV-side action needed — the TV reconnects automatically after the router bounces.
