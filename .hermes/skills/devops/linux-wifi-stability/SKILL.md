---
name: linux-wifi-stability
description: Diagnose and mitigate intermittent Wi-Fi instability on Linux desktops using NetworkManager, kernel/journal evidence, and reversible per-SSID fixes before escalating to router or driver changes.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [wifi, networkmanager, linux, troubleshooting, iwlwifi, verification]
    related_skills: [verification-before-completion, home-router-firewall-review, wayland-session-management]
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
- `journalctl -b -k --no-pager | grep -Ei 'wlan|wifi|iwl|ath|brcm|mt7|rtw|disconnect|deauth|roam|firmware|beacon'`

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
5. Only then consider stronger adapter/driver workarounds.

## Interpreting common patterns

### Beacon-loss + missed-beacon warnings + reconnect loop
Most likely RF/AP/client stability issue. Start with the per-SSID powersave and MAC fixes.

### Good association but app failures only
Likely not a Wi-Fi-layer issue. Check DNS, gateway, captive portal, or upstream connectivity separately.

### DHCP churn after disconnects
Usually downstream of link loss, not the root cause. Fix the radio/link problem first.

## Pitfalls

- Do not jump straight to global config or module parameters when a per-connection fix can isolate the problem.
- Do not confuse router ICMP blocking with no connectivity; some gateways ignore pings.
- Do not treat a successful reconnect as proof of stability.
- Do not over-interpret a single `deauthenticated` line without surrounding journal context.
- On crowded 2.4 GHz, acceptable signal does not rule out channel contention or beacon loss.

## When to write a reference file

Add a `references/` note when you discover adapter- or AP-specific behavior worth reusing, such as Intel AX201 + beacon-loss patterns, a vendor router quirk, or a validated escalation recipe.

Current supporting note:
- `references/intel-ax201-beacon-loss.md`
