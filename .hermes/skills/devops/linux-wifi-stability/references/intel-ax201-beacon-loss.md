# Intel AX201 beacon-loss case note

Observed environment:
- Fedora Silverblue-class desktop/laptop environment
- Intel Wi-Fi 6 AX201 (`iwlwifi`)
- NetworkManager-managed connection
- Active AP on 2.4 GHz, channel 11

Observed evidence pattern:
- `iwlwifi`: `missed beacons exceeds threshold`
- `wpa_supplicant`: `CTRL-EVENT-BEACON-LOSS`
- kernel: `Connection to AP ... lost`
- NetworkManager disconnect/reconnect loops with DHCP restart noise after association loss

Important interpretation:
- DHCP restart spam was downstream noise, not the primary cause.
- The meaningful root signal was repeated beacon loss and AP disconnects while the link had otherwise usable signal.

Safe per-SSID fix that improved the situation immediately:

```bash
nmcli connection modify "$SSID" \
  802-11-wireless.powersave 2 \
  802-11-wireless.cloned-mac-address permanent \
  802-11-wireless.mac-address-randomization 1
nmcli connection down "$SSID" || true
nmcli connection up "$SSID"
```

Post-change verification pattern:
- `nmcli device show <ifname>` showed connected state, IPv4 address, and gateway
- `iw dev <ifname> link` showed stable association to the AP
- `iw dev <ifname> station dump` showed `beacon loss: 0`
- short journal observation window showed no fresh beacon-loss/disconnect events

Practical lesson:
- For Intel AX201 + consumer AP instability, per-SSID powersave-off + permanent-MAC is a good first reversible step before trying system-wide driver parameters.
- If the AP is on crowded 2.4 GHz, next escalation should be band selection (prefer 5 GHz) before deeper driver workarounds.
