# AP-advertised TX power cap (0 dBm)

## Symptom
User reports "1 bar / weak signal on this laptop, but all my other devices show 5 bars."
Other devices (phones, tablets) on the same AP have full signal; Linux laptop does not.

## Kernel evidence
Appears once in the boot journal at association time:

```
wlp0s20f3: Limiting TX power to 0 (-128 - 0) dBm as advertised by <BSSID>
```

Compare with a healthy AP:
```
wlp0s20f3: Limiting TX power to 20 (20 - 0) dBm as advertised by <BSSID>
```

## Grep to catch it
```bash
journalctl -b -k --no-pager | grep -i txpower
```

## Root cause
The AP includes a TX power constraint in its 802.11 regulatory IE. The Linux iwlwifi driver
honours the constraint strictly. Many other devices (Android, iOS, Windows) either ignore it
or interpret it differently. When the AP advertises 0 dBm the Linux radio effectively stops
transmitting — causing apparent 1-bar signal even with a strong AP RSSI.

## Known offenders
- Android Pixel hotspot (tested: Pixel, Pixel_2197 SSID, BSSID 16:EC:EB:9D:73:DC)
  — consistently advertises 0 dBm TX power cap
- Any consumer router with misconfigured country/regulatory settings

## Fix
Same per-SSID profile as the powersave/beacon-loss fix:

```bash
SSID="YourSSID"
nmcli connection modify "$SSID" \
  802-11-wireless.powersave 2 \
  802-11-wireless.cloned-mac-address permanent \
  802-11-wireless.mac-address-randomization never
nmcli connection down "$SSID" || true
nmcli connection up "$SSID"
```

After reconnect the adapter re-negotiates and the kernel should log a higher TX power limit
(e.g. 20 dBm) for the new association.

## Verification
Check `iw dev <ifname> station dump`:
- NSS2 on both TX and RX (both spatial streams active) = fix worked
- NSS1 TX, NSS2 RX = power still throttled

Also check:
```bash
journalctl --since '-1 minute' -k | grep txpower
```
Should now show a non-zero limit.

## Session reference
Observed: Fedora Silverblue, Intel AX201 (iwlwifi), August 2026.
- First SSID (Pixel hotspot): TX power capped to 0 dBm → fixed
- Second SSID (144McKinnonNetwork, A8:42:A1:3C:9C:23): TX power 20 dBm → already healthy
- Remaining "worse than other devices" gap on 144McKinnonNetwork traced to 2.4 GHz channel
  congestion (ch11, multiple neighbours) + lack of 5 GHz band on router — software-only limit,
  not fixable without router config change.
