# Galina's TV — Device Profile and Connectivity Reference

Updated: 2026-09-02

## Network identity

- LAN IP: 192.168.1.100
- MAC: 80:c7:55:8f:94:29
- OUI vendor: **Panasonic Appliances Company** (JP, MA-L block 80C755)
- Confirmed by MAC OUI lookup + SOAP API response on port 55000

## Open ports (confirmed)

| Port  | Service                        | Notes |
|-------|--------------------------------|-------|
| 55000 | Panasonic VIERA UPnP/SOAP API  | Responds to RenderingControl SOAP calls |

## Closed / not present

| Port | Service   | Implication |
|------|-----------|-------------|
| 7000 | AirPlay   | **No AirPlay** — iPad cannot mirror wirelessly |
| 8008 | Chromecast | Not a Chromecast |
| 1925 | LG Connect | Not an LG |
| 80   | Web UI    | Returns 403 Forbidden |

## Wireless display capabilities

- AirPlay: **NO** (port 7000 closed)
- Miracast / Screen Mirroring: Likely available (Panasonic VIERA smart TVs have this menu option)
  but iPads do NOT support Miracast — this does not help iPad users
- Chromecast: NO

## iPad connectivity options (in order of simplicity)

1. **Wired adapter** (recommended, works now, ~$20-30 AUD)
   - Lightning to HDMI adapter (iPad pre-2022) or USB-C to HDMI (iPad 2022+)
   - Plug into iPad charging port + HDMI cable to TV — works instantly

2. **Apple TV dongle** (~$150 AUD, wireless)
   - Adds AirPlay to any HDMI TV
   - iPad mirrors wirelessly with no wires

3. **Chromecast with Google TV** (~$60 AUD, wireless)
   - Google Cast only — iPad needs Google Home app + YouTube/Netflix cast
   - NOT full screen mirroring; app-by-app cast only

## Confirming iPad connector type

- Lightning (older, rectangular with small hole): iPads up to ~2022
- USB-C (oval, no hole): iPad Pro 2018+, iPad Air 2020+, all iPads from late 2022+

## How to identify an unknown TV on LAN

```bash
# 1. Ping sweep to populate ARP table
for i in $(seq 1 254); do ping -c1 -W1 192.168.1.$i &>/dev/null & done; wait

# 2. Grab live IPs and MACs
ip neigh show | grep -v 'FAILED\|INCOMPLETE' | sort -t. -k4 -n

# 3. Look up MAC OUI (3 approaches)
# Fast API:
curl -s "https://api.maclookup.app/v2/macs/80:c7:55:8f:94:29" | python3 -m json.tool | grep company

# 4. Probe TV-specific ports
for port in 55000 8008 1925 7000 7100 8060 80 8080; do
  timeout 1 bash -c "echo > /dev/tcp/192.168.1.100/$port" 2>/dev/null && echo "OPEN: $port"
done

# Port meanings:
# 55000 = Panasonic VIERA (SOAP API)
# 8008  = Chromecast / Google Cast
# 1925  = LG Connect (webOS)
# 7000  = AirPlay receiver (Apple TV, AirPlay-enabled TVs)
# 7100  = AirPlay mirroring stream
# 55001 = Samsung SmartThings
# 8080  = Many Android TVs / generic web UIs

# 5. Confirm Panasonic VIERA with SOAP call
curl -s --connect-timeout 5 -X POST http://192.168.1.100:55000/dmr/control_0 \
  -H 'Content-Type: text/xml; charset=utf-8' \
  -H 'SOAPACTION: "urn:schemas-upnp-org:service:RenderingControl:1#GetVolume"' \
  -d '<?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:GetVolume xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1"><InstanceID>0</InstanceID><Channel>Master</Channel></u:GetVolume></s:Body></s:Envelope>'
# Success response contains <CurrentVolume>NN</CurrentVolume>
# Confirms: Panasonic VIERA with active network

# 6. Check for AirPlay (the key question for iOS pairing)
timeout 1 bash -c 'echo > /dev/tcp/TV_IP/7000' 2>/dev/null && echo 'AirPlay: YES' || echo 'AirPlay: NO'
```

## Decision tree: device-to-TV pairing

```
Is port 7000 open?
  YES → AirPlay receiver present → iOS/macOS can mirror wirelessly
  NO  → Check port 8008?
    YES → Chromecast present → use Google Home app (cast only, not full mirror for iOS)
    NO  → Check port 55001?
      YES → Samsung SmartThings → Samsung DeX or SmartThings app
      NO  → No wireless display option → use wired adapter or add a dongle
```

## VIERA SOAP API notes

- Volume: RenderingControl on `/dmr/control_0`
- NRC (network remote control) on `/nrc/control_0` — requires PIN auth for most actions
- Device model NOT exposed without auth (403 on device description XML)
- Volume confirmed at 57 during 2026-09-02 session
