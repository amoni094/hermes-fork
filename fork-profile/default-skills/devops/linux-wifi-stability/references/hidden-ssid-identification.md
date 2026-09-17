# Hidden SSID Identification — Worked Example

Live-verified Aug 2026 on Fedora Silverblue, wlp0s20f3 (Intel AX201), neighborhood scan.

## The Problem

`nmcli dev wifi list` showed two entries with `--` (no SSID), both on channel 6:

```
8E:78:48:94:F0:6B  --   Infra  6   270 Mbit/s  45  WPA2 WPA3
8A:78:48:94:F0:6B  --   Infra  6   270 Mbit/s  45  WPA2
```

## Investigation Steps

### 1. Full iw scan to extract beacon data

```bash
sudo iw dev wlp0s20f3 scan 2>/dev/null | grep -A 80 'BSS 8e:78:48'
sudo iw dev wlp0s20f3 scan 2>/dev/null | grep -A 80 'BSS 8a:78:48'
```

### 2. What the scan revealed

**Hidden AP 1: 8E:78:48:94:F0:6B**
- freq: 2437 MHz (channel 6), 2.4 GHz band
- signal: -73 dBm
- RSN: PSK + SAE (WPA2/WPA3 mixed), MFP-capable
- BSS Load: station count: 1 (has a connected device)
- HE capabilities present (WiFi 6 capable)
- Country: AU, Environment: bogus (router didn't set correctly)
- OUI 78:48:94 matches known neighbor "Coppermind" (BSSID 84:78:48:94:F0:6C)

**Hidden AP 2: 8A:78:48:94:F0:6C**
- freq: 5200 MHz (channel 40), 5 GHz band
- signal: -82 dBm
- RSN: PSK only (WPA2), no MFP
- BSS Load: station count: 0 (idle)
- Same OUI base as above
- Country: AU

### 3. OUI Cross-Reference

The named AP "Coppermind" had BSSID `84:78:48:94:F0:6C`.
The hidden APs had BSSIDs `8E:78:48:94:F0:6B` and `8A:78:48:94:F0:6C`.

All three share OUI `78:48:94` with only the first octet differing:
- `84` = primary MAC (real hardware address)
- `8E` = locally-administered variant (bit 1 of octet 1 set = LA bit)
- `8A` = another locally-administered variant

This is standard behavior for routers/APs running multiple virtual BSSIDs:
the hardware has one real MAC and generates additional locally-administered
MACs for each virtual interface (guest, IoT, hidden management, etc.).

### 4. Conclusion

Both hidden SSIDs are the **Coppermind** AP next door:
- `8E:78:48:94:F0:6B` = Coppermind's 2.4 GHz secondary/hidden interface (1 client connected)
- `8A:78:48:94:F0:6C` = Coppermind's 5 GHz secondary/hidden interface (idle)

Not a rogue network.

## Pattern: Locally-Administered MAC Detection

A MAC is locally-administered if bit 1 of the first octet is set:
- First octet in binary, second bit from right = 1 → locally administered
- Examples of locally-administered first octets: 02, 06, 0A, 0E, 12, ... 8A, 8E, ...
- Real (globally unique) OUI: first octet has that bit = 0 (00, 04, 08, 0C, ... 84, 88, ...)

Quick check: `printf '%d\n' 0x8E` → 142, `142 & 2` = 2 (locally administered)

## When a Hidden SSID Warrants Real Investigation

- OUI matches no known visible neighbor
- Strong signal that appears/disappears on a schedule
- BSS Load shows clients connecting at unusual hours
- `iw scan` shows unusual capabilities (e.g. high TX power, unusual country code)
- Multiple scans show the same BSSID on different channels (hopping)

In those cases, run repeated scans 10–15 min apart and compare BSS Load station
counts and timing patterns to characterize usage.
