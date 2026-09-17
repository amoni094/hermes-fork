#!/usr/bin/env bash
# Split-tunnel routes for Groq (api.groq.com / console.groq.com)
# Bypasses ProtonVPN so Groq's Cloudflare IPs are reached via home gateway.
# Groq blocks datacenter/VPN ASNs at the CF level; home IP works fine.
#
# Run automatically at login via ~/.config/autostart or call manually.
# Routes are non-persistent — they reset on reboot, so this script re-applies them.

GW="192.168.0.1"
DEV="wlp0s20f3"

for IP in 172.64.149.20 104.18.38.236; do
    if ! ip route show "$IP/32" | grep -q "$IP"; then
        ip route add "${IP}/32" via "$GW" dev "$DEV" 2>/dev/null && \
            echo "Added route: $IP via $GW ($DEV)" || \
            echo "Route $IP already exists or failed (ok)"
    else
        echo "Route $IP already present"
    fi
done
