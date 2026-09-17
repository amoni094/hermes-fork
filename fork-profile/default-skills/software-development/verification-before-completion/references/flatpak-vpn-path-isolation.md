# Flatpak / VPN path isolation

Use when:
- `flatpak update` fails for Flathub or another CDN-backed remote after local repair succeeds
- summary metadata fetches succeed but individual object downloads fail
- the failure is intermittent or remote-specific and smells like TLS/CDN transport rather than package state

Core idea
- Test the same failing URL over different network paths before blaming Flatpak state.
- If the same object succeeds on the physical interface but fails through the VPN/tunnel, the blocker is the network path.

Minimal workflow
1. Capture one concrete failing URL.
   - Good candidates: `summary.idx`, the resolved `summaries/<hash>.gz`, or a specific `objects/<xx>/<sha>.filez` path.
2. Probe it directly with `curl`.
   - Header check: `curl -I --max-time 30 <url>`
   - Body fetch: `curl --max-time 120 -o /tmp/probe <url>`
3. Repeat bound to specific interfaces.
   - Tunnel: `curl --interface <vpn-iface> --max-time 120 -o /tmp/probe-vpn <url>`
   - LAN/Wi-Fi: `curl --interface <lan-iface> --max-time 120 -o /tmp/probe-lan <url>`
4. Compare outcomes.
   - VPN fails, LAN succeeds -> network-path blocker
   - both fail -> likely broader remote/CDN or host TLS issue
   - both succeed but Flatpak fails -> return to Flatpak remote/config/state investigation
5. Only after that decide whether to repair Flatpak, change remotes, or treat it as a VPN-specific transport issue.

What to report
- The exact URL tested
- Which interface(s) were used
- Whether headers succeeded but body fetch failed
- The concrete divergence, e.g. `curl exit 56 on proton0; success on wlp0s20f3`
- Whether the Flatpak problem is now package-state or network-path

Pitfalls
- Treating `remote-ls --updates` as authoritative when targeted update/install says `Nothing to update`
- Assuming repo corruption after `flatpak repair` if direct object fetches already prove a path-specific network failure
- Testing only metadata endpoints; object downloads can fail even when `summary.idx` works
- Claiming Flatpak is fixed while the VPN path remains unverified
