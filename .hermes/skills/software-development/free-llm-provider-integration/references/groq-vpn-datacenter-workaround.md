# Groq + VPN Datacenter IP Blocking Workaround

## Problem

Groq uses Cloudflare with strict bot protection that **blocks all datacenter and VPS IP ranges at the network layer**, preventing access from:
- Headless Chromium/CDP on Fedora Atomic (sandboxed, routed through datacenter IPs)
- ProtonVPN AU/EU servers (route through datacenter ASNs like Host Universal Pty Ltd AS136557)
- Any residential VPN or hosting provider IP range

The error appears at both console.groq.com and api.groq.com:
```
{"error":{"message":"Access denied. Please check your network settings."}}
```

This is **not a network connectivity issue** — it's Cloudflare detecting the source ASN and rejecting it before the request reaches Groq's servers.

## Root Cause

Cloudflare's bot protection fingerprints the Autonomous System Number (ASN) of the incoming IP. Datacenter ASNs (hosting providers, VPN providers using datacenter infrastructure) are blocked. Residential/home ISP ASNs are allowed.

Examples:
- Host Universal Pty Ltd (AS136557) — blocked
- ProtonVPN AU via datacenter carrier — blocked
- Your home ISP residential IP — allowed

## Solution: Split-Tunnel Routing

Route Groq's Cloudflare IPs (172.64.149.20, 104.18.38.236) directly through your home gateway, **bypassing the VPN entirely for Groq traffic only**. Everything else stays on the VPN.

### Implementation

**One-time setup:**

```bash
# Get Groq's Cloudflare IPs
dig +short api.groq.com
# 172.64.149.20
# 104.18.38.236

# Get your home gateway
ip route show default
# default via 192.168.0.1 dev wlp0s20f3 proto dhcp src 192.168.0.185 metric 600

# Add split-tunnel routes (replace gateway and interface with your values)
sudo ip route add 172.64.149.20/32 via 192.168.0.1 dev wlp0s20f3
sudo ip route add 104.18.38.236/32 via 192.168.0.1 dev wlp0s20f3
```

**Persistent (systemd user service):**

Create `~/.config/systemd/user/groq-split-tunnel.service`:
```ini
[Unit]
Description=Groq split-tunnel routes (bypass VPN for Groq)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash /var/home/rainbow/.hermes/scripts/groq-split-tunnel.sh
RemainAfterExit=yes

[Install]
WantedBy=default.target
```

Create `/var/home/rainbow/.hermes/scripts/groq-split-tunnel.sh`:
```bash
#!/usr/bin/env bash
# Split-tunnel routes for Groq (api.groq.com / console.groq.com)
# Bypasses VPN so Groq's Cloudflare IPs are reached via home gateway.

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
```

Enable and start:
```bash
chmod +x ~/.hermes/scripts/groq-split-tunnel.sh
systemctl --user daemon-reload
systemctl --user enable groq-split-tunnel.service
systemctl --user start groq-split-tunnel.service
```

### Verify

```bash
# Check routes are present
ip route show 172.64.149.20
ip route show 104.18.38.236

# Test Groq API
curl -s -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"OK"}],"max_tokens":5}'
```

Should return valid JSON response, not "Access denied" error.

## Notes

- Routes persist only for the current boot. The systemd service re-applies them at login.
- The service type is `oneshot` with `RemainAfterExit=yes` so it doesn't repeatedly run.
- You can check service status: `systemctl --user status groq-split-tunnel.service`
- Groq API calls will use your real home IP for Cloudflare checks; ProtonVPN still encrypts and protects everything else.
- This approach works for any provider that blocks datacenter/VPN IPs (e.g., some job boards, anti-bot tools).

## Alternatives (not recommended)

1. **Disconnect VPN temporarily** — works but manual each time
2. **Use OpenRouter as proxy** — Groq models available through OpenRouter's endpoint; less direct but no Cloudflare blocking
3. **Whitelist with Groq support** — not available on free tier
