#!/usr/bin/env bash
# ProtonVPN Melbourne fallback script
# Runs at boot: if the VPN connection has no internet, cycles through Melbourne servers.
# Servers are ordered by preference (current first, then alternates by load).
# Uses nmcli to modify the WireGuard peer on the existing NM connection.
#
# Deploy to: ~/.local/bin/protonvpn-fallback.sh (chmod +x)
# Enable via: systemctl --user enable protonvpn-fallback.service

set -euo pipefail

CONN="ProtonVPN AU#291"
LOG_TAG="protonvpn-fallback"
TEST_INTERNET="8.8.8.8"
CHECK_RETRIES=5
CHECK_INTERVAL=3    # seconds between each retry
SWITCH_WAIT=8       # seconds to wait after reconnecting before re-testing

# Melbourne servers: "pubkey|ip:port"
# Order: current first (will be skipped), then alternates sorted by load.
# Update from serverlist.json periodically — see SKILL.md for the parse command.
# Current pairs are in references/protonvpn-melbourne-servers.md
SERVERS=(
  "enwR3M+w4F/8bBPz85kf46hh/dVSmQfeoQnECaLo1lo=|144.48.38.178:443"
  "FgeJr7RyQiEKpXVchUYzFsB7p6Ir8fJAA/LqATLjfgY=|144.48.38.98:443"
  "22eXRgMiS/iVgGxxksbmlk1JDgFoV7RXPvGLuaCOPiY=|103.108.229.18:443"
  "DBGcLTkmP+P/0coBrPtXWst9JvST4cufH3KH6h1rFyk=|79.127.155.65:443"
)

log() { logger -t "$LOG_TAG" "$*"; echo "[$(date '+%H:%M:%S')] $*"; }

vpn_connected() {
  nmcli -t -f NAME,STATE connection show --active 2>/dev/null | grep -q "^${CONN}:activated"
}

internet_ok() {
  ping -c 1 -W 3 "$TEST_INTERNET" &>/dev/null
}

wait_for_connectivity() {
  local attempts=$1
  local interval=$2
  for ((i=1; i<=attempts; i++)); do
    if vpn_connected && internet_ok; then
      return 0
    fi
    log "Attempt $i/$attempts: VPN not ready, waiting ${interval}s..."
    sleep "$interval"
  done
  return 1
}

switch_to_server() {
  local pubkey="$1"
  local endpoint="$2"
  log "Switching to endpoint $endpoint (pubkey: ${pubkey:0:20}...)"

  nmcli connection modify "$CONN" \
    wireguard.peers "${pubkey} allowed-ips=0.0.0.0/0 endpoint=${endpoint}"

  nmcli connection down "$CONN" 2>/dev/null || true
  sleep 1
  nmcli connection up "$CONN"
  log "Connection bounced, waiting ${SWITCH_WAIT}s for tunnel..."
  sleep "$SWITCH_WAIT"
}

# ---- Main ----

log "Starting VPN boot check..."

# Give NM a moment to bring up autoconnect on fresh boot
sleep 5

if wait_for_connectivity "$CHECK_RETRIES" "$CHECK_INTERVAL"; then
  log "VPN is up and internet is reachable. Nothing to do."
  exit 0
fi

log "VPN not working. Starting Melbourne server fallback..."

CURRENT_PEER=$(nmcli -g wireguard.peers connection show "$CONN" 2>/dev/null | awk '{print $1}')
log "Current peer pubkey: ${CURRENT_PEER:0:20}..."

for entry in "${SERVERS[@]}"; do
  pubkey="${entry%%|*}"
  endpoint="${entry##*|}"

  if [[ "$pubkey" == "$CURRENT_PEER" ]]; then
    log "Skipping current server (${endpoint}) — already failed."
    continue
  fi

  switch_to_server "$pubkey" "$endpoint"

  if wait_for_connectivity 4 3; then
    log "SUCCESS: Connected via $endpoint"
    exit 0
  else
    log "Server $endpoint failed, trying next..."
  fi
done

# All alternates failed — retry original as last resort
log "All alternates failed. Retrying original server as last resort..."
ORIG="${SERVERS[0]}"
switch_to_server "${ORIG%%|*}" "${ORIG##*|}"
if wait_for_connectivity 5 5; then
  log "SUCCESS: Original server came good."
  exit 0
fi

log "ERROR: All Melbourne servers failed. Manual intervention required."
exit 1
