# Asus Router Hardening Checklist (AX-series)

Live-verified Aug 2026 on Asus AX-series router at 192.168.0.1 (OUI A8:42:A1 — Asus,
not TP-Link as some OUI tables suggest; always verify via macvendorlookup.com).

---

## Security hardening steps (Asus admin UI)

All settings are in the Asus router web UI at http://192.168.0.1 or http://router.asus.com.

### 1. WPA2/WPA3 mixed mode (or WPA3-only)
Path: Wireless > Wireless Security (repeat for 2.4 GHz and 5 GHz tabs)
- Authentication Method: WPA2/WPA3-Personal
- If all devices support WPA3: use WPA3-Personal only
- Do NOT use WPA2-only — WiFi 6 (HE) operates without PMF protection under WPA2-only

After enabling WPA3 on router, update the NM profile:
```bash
# For WPA2/WPA3 mixed — wpa-psk works with MFP negotiation
nmcli connection modify "MySSID-5G" 802-11-wireless-security.key-mgmt wpa-psk
nmcli connection modify "MySSID-5G" 802-11-wireless-security.pmf 2

# For WPA3-only (SAE)
nmcli connection modify "MySSID-5G" 802-11-wireless-security.key-mgmt sae
nmcli connection modify "MySSID-5G" 802-11-wireless-security.pmf 3
nmcli connection up "MySSID-5G"
```

### 2. Disable WPS
Path: Wireless > WPS > Enable WPS: Off
Rationale: WPS PIN is brute-forceable in hours. No benefit if you have the passphrase.

### 3. Router WAN DNS
Path: WAN > WAN DNS Setting
- DNS Server 1: 1.1.1.1
- DNS Server 2: 1.0.0.1
Rationale: Catches devices that ignore DHCP DNS (smart TVs, IoT). Devices with manually
set DNS (PS5, LG TV, laptop via VPN) are unaffected — their override takes priority.

### 4. Confirm 5 GHz channel bandwidth
Path: Wireless > General > 5 GHz tab
- Channel Bandwidth: 80 MHz or 160 MHz (NOT 20/40 Auto)
- Channels: 36 or 149 are clean in typical AU suburban neighborhoods
- AX201 successfully negotiated 160 MHz HE on this router → 490/1297 Mbps TX/RX

### 5. Guest network for IoT device isolation
Path: Guest Network > Add (5 GHz preferred for capable devices)
- SSID: e.g. "guests" or "iot"
- AP Isolation: On (prevents inter-device communication)
- Access Intranet: Off
Rationale: TV, smart speakers, IoT devices should not reach the LAN segment
containing the NAS, laptop, PS5 etc.

### 6. IPv6 stable-privacy on NM profiles (client-side)
```bash
nmcli connection modify "MySSID-5G" ipv6.addr-gen-mode stable-privacy
```
Prevents tracking via stable EUI-64 IPv6 addresses across networks.

---

## Hermes sudo limitation workaround (non-PTY shell)

Hermes runs in a non-interactive shell and cannot respond to sudo password prompts.
When sudo is required for multiple operations, use a pre-built script approach:

```bash
# Hermes pre-builds the script (no sudo needed for this step):
cat << 'SCRIPT' > /tmp/netfix.sh
#!/bin/bash
set -e
# Step 1
tee /etc/modprobe.d/iwlwifi.conf << 'EOF'
options iwlwifi power_save=0 uapsd_disable=3
options iwlmvm power_scheme=1
EOF
# Step 2
mkdir -p /etc/systemd/resolved.conf.d
tee /etc/systemd/resolved.conf.d/dnssec.conf << 'EOF'
[Resolve]
DNSSEC=allow-downgrade
Cache=yes
EOF
systemctl restart systemd-resolved
# Step 3
modprobe -r iwlmvm iwlwifi && modprobe iwlwifi
echo "ALL DONE"
SCRIPT
chmod +x /tmp/netfix.sh
```

User runs one command: `sudo /tmp/netfix.sh`
Password prompt appears once; all steps complete atomically.

This is the reliable pattern when:
- Multiple files need writing to /etc/ in sequence
- sudo -v cache does not persist across Hermes tool calls
- NOPASSWD sudoers is not configured

---

## Post-migration 5 GHz performance (live-verified Aug 2026)

After enabling 5 GHz and creating NM profile with band="a":

| Metric | Before (2.4 GHz ch1) | After (5 GHz ch44, 160 MHz) |
|---|---|---|
| TX rate | 146 Mbps HE-MCS 7 | 1152 Mbps HE-MCS 5 |
| RX rate | 258 Mbps HE-MCS 10 | 1297 Mbps HE-MCS 6 |
| Signal | -54 dBm | -58 dBm |
| Channel width | 20 MHz | 160 MHz |
| TX retries | ~8.3% | (drops significantly after power_scheme=1) |

Neighborhood 5 GHz was nearly empty: only 4 APs visible vs 15 on 2.4 GHz.
UNII-1 (5180–5240 MHz) had no co-channel competition in this scan.
