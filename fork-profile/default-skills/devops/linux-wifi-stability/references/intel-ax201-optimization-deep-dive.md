# Intel AX201 WiFi 6 Optimization — Deep Dive Reference

Live-verified on: Fedora Silverblue 44, kernel 7.1.8, NetworkManager, Intel AX201 (iwlwifi/iwlmvm)

---

## Environment snapshot

- NIC: `wlp0s20f3`, Intel Wi-Fi 6 AX201, 2×2 MIMO, HE (WiFi 6) active
- Router: Asus (OUI A8:42:A1), BSSID A8:42:A1:3C:9C:23
- Gateway: A8:42:A1:3C:9C:24 (one MAC above = LAN/WAN port of same device)
- Signal: −52 dBm (good); TX 172 Mbps HE-MCS 7, RX 229 Mbps HE-MCS 9
- TX retry rate: ~8% (8249/99k packets — elevated, target <5%)
- ProtonVPN WireGuard always-on (proton0, AU#377)
- iwlwifi power_save: N (disabled ✓); uapsd_disable: 3 (disabled ✓); 11n_disable: 0 ✓
- iwlmvm power_scheme: **2 (balanced — suboptimal, should be 1)**
- PMF (802-11-wireless-security.pmf): **0/default = disabled — should be at least 2**

---

## 1. Why the NIC stays on 2.4 GHz despite supporting 5 GHz

Root cause is **router-side**, not client-side. `nmcli dev wifi list` showed only ONE
BSSID (A8:42:A1:3C:9C:23) for the SSID — on channel 1 (2.4 GHz). The Asus router's
5 GHz radio was not advertising anything. No 5 GHz BSSID existed for NM to choose.

NetworkManager does not "prefer" a band if no AP in that band is visible. The NIC is
not stuck — it correctly associates with the only available BSSID.

**Fix (router-side first):**
- Log into Asus admin (http://192.168.1.1 or http://router.asus.com)
- Wireless > General > enable 5 GHz radio
- Either same SSID (Smart Connect) or separate SSID (e.g. `MyNetwork_5G`)

**Fix (client-side, once 5 GHz BSSID is visible):**
```bash
# Create a 5 GHz-only NM profile
nmcli connection add type wifi ssid "MySSID" \
  con-name "MySSID-5G" \
  802-11-wireless.band "a" \
  802-11-wireless.powersave 2 \
  connection.autoconnect-priority 10

nmcli connection modify "MySSID-5G" \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.psk "PASSWORD"

# Lower 2.4 GHz profile priority
nmcli connection modify "MySSID" connection.autoconnect-priority 0
```

`band "a"` locks wpa_supplicant to 5 GHz (VHT/HE) bands only.
Optionally pin to a specific 5 GHz BSSID: `802-11-wireless.bssid "XX:XX:XX:XX:XX:XX"`

---

## 2. TX retry rate: diagnosis and fixes

**8% is elevated** (acceptable: <5%). Root causes in priority order:

1. **Co-channel interference on ch 1** — two APs on ch 1 in the scan.
   CSMA/CA backoff triggers when stations transmit simultaneously.
   Channel 1 was still the least-congested 2.4 GHz channel in this specific scan
   (ch 6 had 4 APs, ch 11 had 2+). Don't change channel unless retries worsen.

2. **iwlmvm power_scheme=2 (balanced)** — even with NM powersave disabled, MVM
   firmware's own power logic can introduce timing gaps that cause retry-inducing
   collisions. Fix: set power_scheme=1 (see modprobe section below).

3. **Rate selection mismatch** — HE-MCS 7 at −52 dBm is borderline if noise floor
   is elevated by neighbor APs. minstrel_ht retries at lower MCS before dropping
   rate, inflating retry counters.

4. **Bluetooth coexistence** — AX201 shares antenna complex with BT. Heavy BT
   transfers during WiFi use cause TXCoex-triggered retries. Disable BT if unused:
   `rfkill block bluetooth`

**Verify retry rate:**
```bash
iw dev wlp0s20f3 station dump | grep -E "(retries|tx packets)"
```

---

## 3. Channel width: 20 MHz vs 40 MHz on 2.4 GHz

**Verdict: keep 20 MHz.** Do NOT enable 40 MHz on 2.4 GHz in this dense neighborhood.

Reasoning:
- 2.4 GHz has only ~83 MHz usable (AU). Only 3 non-overlapping 20 MHz channels (1, 6, 11).
- 40 MHz at center ch 1 would span channels 1–7, absorbing interference from 6+ neighbor
  APs currently on channels 2, 3, 4, 5 that are NOT competing with you today.
- 802.11n 20/40 BSS coexistence mechanism will likely force the router back to 20 MHz
  anyway when it detects overlapping BSSes — a compliant AP (Asus is) does this automatically.
- Each doubling of channel width adds ~3 dB of noise floor (doubled noise bandwidth, per
  Ekahau channel planning principle).
- Real-world result in dense deployments: 40 MHz often performs WORSE than 20 MHz.

On 5 GHz, 80 MHz is safe — channels 36, 40, 44, 48 (UNII-1) or 149–161 (UNII-3) are
clean in this specific scan (only distant weak signals at those channels).

---

## 4. PMF (Management Frame Protection) — WPA-PSK + WiFi 6

**Current state:** `802-11-wireless-security.pmf: 0 (default)` → ieee80211w=0 → **disabled**

PMF protects management frames (deauth, disassoc, action) with cryptographic MIC.
Without it, any nearby radio can forge a deauth frame and force a disconnect.
This is the basis of deauth floods and WPA handshake capture attacks (used in offline
dictionary attacks against WPA2-PSK).

**IEEE 802.11ax (WiFi 6) mandates PMF** for HE connections — ieee80211w=1 minimum.
The NIC is actively connecting in HE mode (confirmed by HE-MCS rates). Consumer Asus
routers on WPA2-PSK don't strictly enforce this (WPA3-SAE does), but leaving it
disabled is technically non-compliant and exposes the connection to deauth attacks.

**NM PMF values:**
- 0 = default (for WPA-PSK this resolves to disabled)
- 1 = disable (explicit)
- 2 = optional (ieee80211w=1 — negotiate, accept non-PMF APs)
- 3 = required (ieee80211w=2 — refuse to connect without PMF)

**Recommended action:**
```bash
# Start with optional — compatible, negotiated
nmcli connection modify "MySSID" 802-11-wireless-security.pmf 2
nmcli connection up "MySSID"

# If stable, upgrade to required (Asus AX routers support this)
nmcli connection modify "MySSID" 802-11-wireless-security.pmf 3
nmcli connection up "MySSID"
```

No throughput impact — PMF applies only to management frames, not data frames.
Compatibility: Asus AX-series routers (2019+) all support PMF=required.

---

## 5. iwlwifi/iwlmvm modprobe parameters for AX201

All parameters confirmed from `modinfo iwlwifi` / `modinfo iwlmvm` on kernel 7.1.8.

**Recommended `/etc/modprobe.d/iwlwifi.conf`:**
```
# Intel AX201 / iwlwifi + iwlmvm tuning — throughput and stability

# Disable firmware power saving at module load time
# (NM powersave=2 disables per-interface, but this ensures it at driver load)
options iwlwifi power_save=0

# Keep U-APSD disabled (avoids firmware buffering delays)
# Default is already 3 on this system; explicit is safer
options iwlwifi uapsd_disable=3

# Set MVM firmware power scheme to always-on
# Eliminates periodic latency spikes and retry-inducing timing gaps from balanced mode
# 1=always-on, 2=balanced (default), 3=low-power
options iwlmvm power_scheme=1
```

**All available iwlwifi parameters** (from modinfo on this kernel):
```
power_save       bool   enable WiFi power management (default: disable)
power_level      int    default power save level 1-5 (default: 1)
11n_disable      uint   bitmap: 1=full disable, 2=no agg TX, 4=no agg RX, 8=enable agg TX
amsdu_size       int    0=auto (12K for multi-Rx-queue devices like AX201), 1=4K, 2=8K, 3=12K
uapsd_disable    uint   bitmap: 1=BSS, 2=P2P Client (default: 3 = both disabled)
disable_11ac     bool   Disable VHT capabilities (default: false)
disable_11ax     bool   Disable HE capabilities (default: false)
disable_11be     bool   Disable EHT capabilities (default: false)
bt_coex_active   bool   enable wifi/bt co-exist (default: enable)
```

**iwlmvm parameters:**
```
power_scheme     int    1=active, 2=balanced, 3=low-power (default: 2)
```

**DO NOT USE** (these hurt performance):
- `11n_disable=1` — disables all 802.11n aggregation, kills throughput
- `11n_disable=2` — disables TX A-MPDU aggregation, reduces throughput
- `disable_11ax=true` — disables WiFi 6/HE mode entirely
- `disable_11ac=true` — disables VHT, worse on 5 GHz

**Applying on Fedora Silverblue** (`/etc/modprobe.d/` is writable in the overlay):
```bash
sudo tee /etc/modprobe.d/iwlwifi.conf << 'EOF'
options iwlwifi power_save=0
options iwlwifi uapsd_disable=3
options iwlmvm power_scheme=1
EOF

# Apply without reboot (NM reconnects automatically):
sudo modprobe -r iwlmvm iwlwifi && sudo modprobe iwlwifi

# Verify:
cat /sys/module/iwlmvm/parameters/power_scheme   # should print: 1
cat /sys/module/iwlwifi/parameters/power_save     # should print: N
```

**Note on amsdu_size:** Default (0) already selects 12K for multi-Rx-queue devices
like AX201. Only set explicitly if bulk throughput is still low after other fixes.

**Firmware version:** AX201 uses QuZ-a0-hr-b0 firmware. Verify with:
```bash
sudo dmesg | grep iwlwifi | grep "loaded firmware"
rpm -q linux-firmware   # ensure current on Fedora
```

---

## 6. DNS with always-on WireGuard VPN

**Situation:** ProtonVPN WireGuard always-on → DNS 10.2.0.1 (VPN server, inside tunnel)
→ systemd-resolved stub (127.0.0.53) → application.

DNS is already encrypted inside the WireGuard tunnel. This is correct.

**Comparison:**

| Option | Verdict |
|---|---|
| ProtonVPN DNS (10.2.0.1, current) | ✓ Best default. Encrypted in tunnel, no ISP visibility |
| DoH via systemd-resolved | ✗ Redundant with WG. Adds HTTPS overhead. May bypass VPN DNS |
| Local Unbound/dnsmasq | Marginal. systemd-resolved already caches |
| DoT to ProtonVPN | ✗ ProtonVPN doesn't offer DoT at 10.2.0.1 |

**Recommended enhancements:**
```bash
# Enable DNSSEC validation in systemd-resolved
sudo mkdir -p /etc/systemd/resolved.conf.d/
sudo tee /etc/systemd/resolved.conf.d/dnssec.conf << 'EOF'
[Resolve]
DNSSEC=allow-downgrade
Cache=yes
EOF
sudo systemctl restart systemd-resolved

# Verify no DNS leak (should show ProtonVPN server, not ISP)
resolvectl status
# Use dnsleaktest.com to confirm
```

**Killswitch gap:** If VPN drops, DNS falls back to router-advertised ISP DNS (via DHCP).
ProtonVPN's killswitch should block this. Verify:
```bash
# Check which DNS is active per interface
resolvectl status wlp0s20f3
resolvectl status proton0
# proton0 should show 10.2.0.1; wlp0s20f3 DNS should be unused/overridden by routing
```

**Do NOT add DoH** when WireGuard is always-on — the DoH server would need to be inside
the tunnel or you risk DNS queries bypassing the VPN to the DoH provider directly.

---

## Quick summary of priority actions (from this session)

1. **Router:** Enable 5 GHz radio on Asus admin panel (most impactful)
2. **Modprobe:** Create `/etc/modprobe.d/iwlwifi.conf` with power_scheme=1
3. **PMF:** `nmcli connection modify "SSID" 802-11-wireless-security.pmf 2`
4. **5 GHz profile:** Create NM profile with `band "a"`, priority 10 (once router has 5G)
5. **DNSSEC:** Add `DNSSEC=allow-downgrade` to systemd-resolved config
