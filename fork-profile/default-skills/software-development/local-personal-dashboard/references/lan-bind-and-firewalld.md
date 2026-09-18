# LAN-enabling a local dashboard

Use this when a dashboard already works on the current machine and the user wants access from other devices on the same LAN.

## Core lesson
Treat LAN availability as a two-layer verification problem:
1. Application bind address
2. Host firewall / network policy

A dashboard bound only to `127.0.0.1` is local-only even if the route logic is correct. A dashboard bound to `0.0.0.0` may still be unreachable from the LAN if the OS firewall blocks the port.

## Minimal implementation pattern
For lightweight Python HTTP servers, keep three knobs separate:
- `HOST`: serving bind address, typically `0.0.0.0` for LAN reachability
- `PORT`: serving port
- `HEALTHCHECK_HOST`: loopback host for single-instance self-probes, typically `127.0.0.1`

Example pattern:
- app serves on `(HOST, PORT)`
- startup preflight probes `http://HEALTHCHECK_HOST:PORT/healthz`

This preserves single-instance localhost detection while opening the service to the LAN.

## Verification order
1. Read the code and confirm the server bind is not hardcoded to loopback.
2. Restart or relaunch the app.
3. Verify the socket moved off loopback:
   - `ss -ltnp | grep <port>`
   - Success looks like `0.0.0.0:<port>` or the explicit LAN IP, not `127.0.0.1:<port>`.
4. Probe localhost health:
   - `curl http://127.0.0.1:<port>/healthz`
5. Probe the machine's LAN IP from the same machine:
   - `curl http://<lan-ip>:<port>/healthz`
6. Check firewall state separately:
   - `firewall-cmd --state`
   - `firewall-cmd --list-ports`
   - `firewall-cmd --list-services`
7. If firewall changes fail due to privilege, report split status exactly:
   - app-side LAN bind complete
   - firewall opening still required
   - include the exact privileged commands for the user

## Fedora / firewalld note
On Fedora, a successful app bind does not imply cross-device access. If `firewall-cmd` does not show the dashboard port, the app may still be blocked to other LAN devices.

Typical commands:
- `sudo firewall-cmd --add-port=<port>/tcp`
- `sudo firewall-cmd --add-port=<port>/tcp --permanent`
- `sudo firewall-cmd --reload`

## Reporting pattern
Do not say "available to all devices on the LAN" unless both are true:
- the app is bound beyond loopback
- the firewall already allows the port, or you independently verified remote reachability

Preferred wording when privilege is missing:
- "App-side LAN bind is complete and verified; OS firewall still needs one privileged rule before other devices can connect."

## Evidence captured in this session
- Existing dashboard used a fixed loopback bind on `127.0.0.1:8765`.
- Updated pattern introduced `HOST=0.0.0.0` plus `HEALTHCHECK_HOST=127.0.0.1`.
- Verified `ss` showed `0.0.0.0:8765` after restart.
- Verified `/healthz` on both `127.0.0.1:8765` and the machine LAN IP.
- `firewall-cmd --add-port=8765/tcp` failed without privilege, so final status had to remain split rather than claiming universal LAN access.
