---
name: protonvpn-nm-automation
triggers:
  - ProtonVPN on Linux fails to connect on boot
  - VPN not connecting at startup, need fallback server logic
  - Automate ProtonVPN server switching via NetworkManager
  - WireGuard peer manipulation with nmcli
  - Systemd user service for NM-managed VPN on Fedora Silverblue
description: >
  Use when automating ProtonVPN boot failover (NM+WireGuard).
version: 1.0.1
author: Hermes Agent
license: MIT
platforms: [linux]
related_skills:
  - linux-wifi-stability
  - wayland-session-management
metadata:
  hermes:
    tags: [vpn, protonvpn, wireguard, networkmanager, systemd, boot, fedora]
    related_skills: [linux-wifi-stability, wayland-session-management]
---

# ProtonVPN NetworkManager Automation

Use when the user needs automated VPN failover, server switching, or boot
reliability for ProtonVPN on Linux (Fedora Silverblue / Atomic desktop),
where ProtonVPN is installed as a Flatpak and manages its connections via
NetworkManager WireGuard connections.

## Environment facts (this machine)

- ProtonVPN: Flatpak (`com.protonvpn.www`)
- Protocol: WireGuard, managed by NetworkManager as connection `ProtonVPN AU#310` (as of Sep 2026; server number changes when user switches servers)
- NM connection type: `wireguard`, device `proton0` (stable interface name — does not change with server switches)
- Kill-switch: `pvpn-killswitch-ipv6` dummy connection also managed by ProtonVPN
- User linger: enabled (`loginctl show-user rainbow` → `Linger=yes`)
- nmcli: works without sudo for this user to manage NM connections

## Key file locations

- Server list: `~/.var/app/com.protonvpn.www/cache/Proton/VPN/serverlist.json`
- Connection persistence: `~/.var/app/com.protonvpn.www/cache/Proton/VPN/connection/connection_persistence.json`
- Settings: `~/.var/app/com.protonvpn.www/config/Proton/VPN/settings.json`
- Fallback script: `~/.local/bin/protonvpn-fallback.sh`
- Systemd unit: `~/.config/systemd/user/protonvpn-fallback.service`

## Server list parsing

The cached `serverlist.json` top-level key is `LogicalServers` (list of dicts).

Filter for active Melbourne servers:
```python
import json
data = json.load(open('serverlist.json'))
mel = [s for s in data['LogicalServers']
       if s.get('ExitCountry') == 'AU'
       and s.get('City') == 'Melbourne'
       and s.get('Status') == 1]
```

Each logical server has a `Servers` list with physical hosts. Key fields per physical:
- `EntryIP` — the WireGuard endpoint IP
- `X25519PublicKey` — WireGuard peer public key
- Port is always 443 for standard WireGuard over HTTPS

All 72 Melbourne logical servers share only 4 distinct physical IPs/pubkeys.
See `references/protonvpn-melbourne-servers.md` for the current list.

## WireGuard peer manipulation via nmcli

ProtonVPN AU#291's peer format:
```
wireguard.peers: <pubkey> allowed-ips=0.0.0.0/0 endpoint=<ip>:<port>
```

Switch to a different Melbourne server:
```bash
nmcli connection modify "ProtonVPN AU#291" \
  wireguard.peers "<NEW_PUBKEY> allowed-ips=0.0.0.0/0 endpoint=<NEW_IP>:443"

# Bounce to apply — active connection ignores nmcli modify until bounced
nmcli connection down "ProtonVPN AU#291" || true
sleep 1
nmcli connection up "ProtonVPN AU#291"
```

This is a persistent NM modification — survives reboots.
Read current peer pubkey: `nmcli -g wireguard.peers connection show "ProtonVPN AU#291" | awk '{print $1}'`

## Connectivity check

Two-layer check catches tunnels that are "up" but not routing:
1. NM active: `nmcli -t -f NAME,STATE connection show --active | grep "ProtonVPN AU#291:activated"`
2. Real internet: `ping -c 1 -W 3 8.8.8.8`

Do not rely on pinging the ProtonVPN DNS (10.2.0.1) alone — it is reachable
inside the tunnel but does not confirm actual outbound internet routing.

## Systemd user service pattern

For NM automation that must run at boot without user login:

```ini
[Unit]
Description=ProtonVPN Melbourne server fallback on boot
After=NetworkManager-wait-online.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/var/home/rainbow/.local/bin/protonvpn-fallback.sh
TimeoutStartSec=300

[Install]
WantedBy=default.target
```

Enable:
```bash
systemctl --user daemon-reload
systemctl --user enable protonvpn-fallback.service
```

User linger must be enabled for the service to run at boot without login:
```bash
loginctl enable-linger <username>
loginctl show-user <username> | grep Linger   # verify: Linger=yes
```
On this machine linger is already enabled.

Check logs: `journalctl --user -u protonvpn-fallback.service`

## Fallback script design (live at ~/.local/bin/protonvpn-fallback.sh)

Key design decisions:
- 5-second initial sleep to let NM autoconnect complete
- Skip current server (already failed) and try alternates first
- Return to original server as last resort (may have recovered)
- After each switch: wait 8s then retry connectivity 4x at 3s intervals
- Log via `logger -t protonvpn-fallback` and stdout for journalctl

See `templates/protonvpn-fallback.sh` for the canonical template.

## Updating the server list

ProtonVPN IPs rotate periodically. Re-parse the cached serverlist.json:
```bash
python3 -c "
import json
data = json.load(open(
  '/var/home/rainbow/.var/app/com.protonvpn.www/cache/Proton/VPN/serverlist.json'))
mel = [s for s in data['LogicalServers']
       if s.get('ExitCountry')=='AU' and s.get('City')=='Melbourne' and s.get('Status')==1]
seen = set()
for s in sorted(mel, key=lambda x: x.get('Load',99)):
    for p in s.get('Servers',[]):
        ip = p.get('EntryIP'); pk = p.get('X25519PublicKey','')
        if ip not in seen:
            seen.add(ip)
            print(f'{ip} | {pk}')
"
```
Then update the `SERVERS=()` array in `~/.local/bin/protonvpn-fallback.sh` and
update `references/protonvpn-melbourne-servers.md`.

## LAN access while ProtonVPN is active

ProtonVPN's WireGuard interface (`proton0`) captures all traffic via `allowed-ips=0.0.0.0/0`,
which prevents LAN-addressed packets from reaching the local network interface.
Symptom: `ping 192.168.0.X` returns "Destination Host Unreachable" even though both
machines are on the same subnet and have matching /24 addresses.

Workaround — inject a higher-priority host route that bypasses the VPN tunnel:

```bash
sudo ip route add 192.168.0.0/24 dev wlp0s20f3 metric 100
```

Verify routing is fixed:
```bash
ping -c 3 192.168.0.X
```

This route is ephemeral — it survives until the next reboot or NM reconnect event.
To make it persistent, add it as a NM dispatcher script or include it in
`/etc/NetworkManager/dispatcher.d/`.

Note: after adding the route, SSH password auth may still require `PasswordAuthentication yes`
in `/etc/ssh/sshd_config` on the target machine if it was installed with defaults
(Ubuntu/Lubuntu defaults to `yes` but worth checking).

## Tearing down VPN for Miracast / WiFi-Direct sessions

FluxCast and any Miracast/WFD tool use WiFi P2P which is **blackholed by the
ProtonVPN killswitch** — P2P DHCP and RTSP traffic never reaches the TV,
causing silent "device not found" failures even though WiFi is up.

The killswitch (`pvpn-killswitch-ipv6`) has `connection.autoconnect=yes` with
no master connection — it re-arms immediately after `nmcli connection down`
if you only bring down the VPN. You must disable autoconnect first:

```bash
# 1. Bring down VPN
nmcli connection down "ProtonVPN AU#365" 2>/dev/null || true

# 2. Disable killswitch autoconnect THEN bring it down
nmcli connection modify pvpn-killswitch-ipv6 connection.autoconnect no
sleep 0.5
nmcli connection down pvpn-killswitch-ipv6 2>/dev/null || true

# ... do Miracast session ...

# 3. Restore on exit (always in a trap)
nmcli connection modify pvpn-killswitch-ipv6 connection.autoconnect yes
nmcli connection up pvpn-killswitch-ipv6 2>/dev/null || true
nmcli connection up "ProtonVPN AU#365" 2>/dev/null || true
```

Always restore via `trap restore_vpn EXIT INT TERM` so Ctrl-C during casting
doesn't leave the machine unprotected.

The `fluxcast-cast` wrapper at `~/.local/bin/fluxcast-cast` implements this
pattern — use it instead of launching FluxCast directly.

## Boot race guard in fallback scripts

If the fallback service runs before NM has finished activating the WireGuard
profile, `nmcli connection show --active` will show `activating` not `activated`,
causing premature peer-switching. Add a guard before the main connectivity check:

```bash
wait_for_not_activating() {
  local max=${1:-30} interval=${2:-2} n=0
  while nmcli -t -f NAME,STATE connection show --active 2>/dev/null \
        | grep -q ":activating"; do
    ((n++)); [[ $n -ge $max ]] && break
    sleep "$interval"
  done
}

# In main, after the initial sleep:
wait_for_not_activating 15 2
```

## Dynamic CONN resolution (critical for scripts and services)

ProtonVPN renames the NM connection when the user switches servers (AU#291 → AU#310 → AU#365 etc.).
Hardcoding the connection name in a script or service unit is a boot-time landmine — it will silently
fail with "no connection found" exit code 10 and the fallback does nothing.

Instead, resolve the active ProtonVPN connection name dynamically from the stable `proton0` interface:

```bash
# In protonvpn-fallback.sh — resolve at runtime, not at script-write time
resolve_conn() {
  local conn
  # Method 1: find the active connection on the proton0 device
  conn=$(nmcli -t -f NAME,DEVICE connection show --active 2>/dev/null \
    | awk -F: '$2 == "proton0" {print $1}' | head -1)
  [[ -n "$conn" ]] && { echo "$conn"; return; }

  # Method 2: find any WireGuard connection with ProtonVPN in the name (not yet active)
  conn=$(nmcli -t -f NAME,TYPE connection show 2>/dev/null \
    | awk -F: '$2 == "wireguard" && $1 ~ /ProtonVPN/ {print $1}' | head -1)
  echo "$conn"
}

CONN=$(resolve_conn)
if [[ -z "$CONN" ]]; then
  log "ERROR: No ProtonVPN WireGuard connection found. Nothing to do."
  exit 0
fi
log "Using NM connection: $CONN"
```

Verify the resolution works live:
```bash
nmcli -t -f NAME,DEVICE connection show --active | awk -F: '$2 == "proton0" {print $1}'
# Should print the current ProtonVPN AU#NNN connection name
```

## Pitfall: reenable required after changing WantedBy

Changing `WantedBy=` in a `[Install]` section does NOT update existing symlinks.
If you change from `WantedBy=default.target` to `WantedBy=graphical-session.target`,
the old symlink in `default.target.wants/` stays and the new one is never created.
The service appears correct but still starts at the old point.

Fix — always disable+enable after any WantedBy change:
```bash
systemctl --user disable protonvpn-fallback.service
systemctl --user enable protonvpn-fallback.service
# Verify: symlink should now be in graphical-session.target.wants/, not default.target.wants/
find ~/.config/systemd/user/ -name '*protonvpn-fallback*' -ls
```

Verify the WantedBy actually took:
```bash
systemctl --user show protonvpn-fallback.service -p WantedBy
```

## Firewalld zone assignment

When firewalld is active, set zones on the NM connection profiles (not just
via `firewall-cmd --zone=X --add-interface=Y`). Interface assignments made
only through firewall-cmd are lost on NM reconnect events:

```bash
sudo nmcli connection modify "ProtonVPN AU#315" connection.zone trusted
sudo nmcli connection modify "pvpn-killswitch-ipv6" connection.zone drop
sudo nmcli connection modify "144McKinnonNetwork5G" connection.zone home
sudo nmcli connection modify "Wired connection 1" connection.zone home
```

Correct zone mapping for this machine:
- `wlp0s20f3` (WiFi, home SSID) → `home`
- `enp0s20f0u1` (Pixel tether) → `home`
- `proton0` (VPN tunnel) → `trusted`
- `ipv6leakintrf0` (killswitch dummy) → `drop` — nothing should ingress here;
  using `public` (the firewalld default fallback) exposes it unnecessarily

After modifying profiles, reload firewalld to apply:
```bash
sudo firewall-cmd --reload
sudo firewall-cmd --get-active-zones  # verify
```

Note: ProtonVPN recreates the WireGuard NM connection with a NEW UUID whenever
it reconnects after a `connection down`/`connection up` cycle. The old UUID's
zone assignment is gone. Re-run the `nmcli connection modify ... connection.zone`
command on the new connection after any ProtonVPN reconnect that you initiated
manually (normal ProtonVPN-initiated server switches do NOT recreate the UUID).

## Pitfalls

- nmcli WireGuard peer format is strict: one string with all three components (`pubkey allowed-ips=... endpoint=...`) — no extra spaces, nothing missing
- 72 Melbourne logical servers share only 4 physical IPs/pubkeys — switching logical servers on the same IP does nothing; target distinct IP/pubkey pairs only
- `wireguard.peers` modify on an active connection requires a down/up bounce to take effect
- **Do not manually switch ProtonVPN servers via nmcli while the app's autoconnect is active.** When you bounce the NM connection, ProtonVPN's autoconnect fires and recreates the connection with a fresh UUID and its own server choice (usually FASTEST), defeating the manual switch. To switch servers, use the ProtonVPN app UI or CLI, or temporarily disable autoconnect first.
- **flatpak-session-helper boot race**: `flatpak run` fails with `app/com.protonvpn.www/x86_64/stable not installed` if it fires before `flatpak-session-helper.service` is running, even though the app is installed system-wide. The helper starts 3–5s after `graphical-session.target` is satisfied. Fix: add `After=flatpak-session-helper.service` and `Wants=flatpak-session-helper.service` to any user service that runs a system Flatpak at login.
- **firewalld zone on killswitch dummy**: `pvpn-killswitch-ipv6` falls into the `public` default zone when firewalld starts. Explicitly set it to `drop` via both `firewall-cmd --permanent` and `nmcli connection modify ... connection.zone drop`.
- **Killswitch autoconnect trap**: `pvpn-killswitch-ipv6` has `autoconnect=yes` with no master — bringing it down alone causes it to re-arm within 1-2s. Must set `connection.autoconnect no` before `connection down`, and restore `yes` after the session.
- `set -euo pipefail` + `((VAR++))`: when VAR=0, bash treats the result as failure exit code and kills the script. Use `VAR=$((VAR+1))` instead.
- `connection.autoconnect-retries=-1` (default) means NM retries indefinitely — the fallback script complements NM autoconnect, it does not replace it
- VPN must be fully down (not just "activating") before any WiFi P2P operation — use the `wait_for_not_activating` guard above

## Boot race — root cause and fix (Sep 2026)

Symptom: ProtonVPN picks Adelaide (AU#197) instead of Melbourne at boot, causing ~55ms latency instead of ~20ms.

Root cause: three-way race:
1. `protonvpn-autostart.service` had no `network-online.target` dep — could fire before WiFi associated
2. `protonvpn-fallback.sh` exited immediately if no NM WireGuard connection found (WG module loads ~17s after the service ran)
3. Fallback only checked connectivity, not latency — a connected-but-distant server was accepted as healthy

Fixes applied:
- Both service units: `After=... network-online.target` + `Wants=network-online.target`
- Fallback script: retry loop up to 60s (12 × 5s) before giving up on finding NM connection
- `latency_ok()` added — pings 8.8.8.8 through tunnel, rejects if avg RTT > MAX_LATENCY_MS=35 (Adelaide ~55ms, Melbourne ~20ms)
- Fallback service: `TimeoutStartSec=420` (was 300)

Verify after reboot: `journalctl --user -u protonvpn-fallback.service` — should show retry loop, not immediate exit.

## Supporting files

- `references/protonvpn-melbourne-servers.md` — current Melbourne IP/pubkey pairs
- `templates/protonvpn-fallback.sh` — canonical fallback script template
