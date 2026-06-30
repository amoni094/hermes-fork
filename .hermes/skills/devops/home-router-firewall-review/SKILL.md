---
name: home-router-firewall-review
description: Review a desktop firewall plus consumer-router settings for a normal home user, aiming for a solid usable baseline rather than maximum lockdown.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [home-network, router, firewall, gaming, security, wifi, upnp]
    related_skills: [verification-before-completion]
---

# Home Router + Firewall Review

## Overview

Use this skill when a user wants a practical review of their local firewall and consumer-router settings for everyday home use: gaming consoles, web browsing, email, and light development.

Target outcome: a small set of high-value changes with clear tradeoffs, not enterprise hardening.

## When to Use

- The user asks whether their firewall/router settings look okay.
- The user wants a solid baseline for home use.
- The environment is a normal home LAN with a consumer router.
- The user mentions PS5, Xbox, Switch, Steam, browsing, email, or git/dev and does not want extreme lockdown.

## Workflow

1. Inspect the host firewall first.
   - Check whether the host firewall is running.
   - Identify the default zone/profile.
   - List open ports/services.
   - Compare allowed ports against actual listeners.
   - Verify whether listeners are localhost-only or bound to all interfaces.

2. Inspect network routing/DNS context.
   - Check active interfaces, default route, and DNS.
   - Note whether a VPN is active.
   - Avoid overreacting to localhost listeners; prioritize externally reachable exposure.

3. Review the router live if possible.
   - Prefer read-only inspection first.
   - Check: firewall/SPI, ping response from WAN, UPnP, DMZ, manual port forwards, remote admin, WPS, Wi‑Fi security, IPv6, firmware/update status.
   - If browser clicks are flaky in SPA router UIs, route directly by URL hash or page state inspection rather than assuming the menu click failed.
   - On TP-Link AX55-class UIs, expect browser sessions to reset back to the login screen mid-review; if a page suddenly goes blank or ref IDs fail, re-navigate to the router URL, re-authenticate, then continue with hash-route inspection.
   - Do not batch-set multiple hash routes in one browser-console expression; some router SPAs can land on `about:blank` during that pattern. Change one route at a time and re-read the page after each navigation.
   - For TP-Link Administration pages, do not assume there is always a separate WAN HTTP/HTTPS selector. Some AX55 firmware exposes only `Local Management via HTTPS` plus a `Remote Management` toggle, which means the absence of an HTTP option is itself an important finding.

4. Give a practical recommendation set.
   - Separate must-change items from optional hardening.
   - Keep gaming usability in view.
   - Explain tradeoffs for UPnP and remote admin instead of treating them as automatic failures.

5. If credentials were shared in chat or typed into a router UI during the session, recommend rotating them afterward.

## Baseline Recommendations

For a normal home user who wants solid and usable:

- Host firewall on.
- Public/untrusted zone/profile for Wi‑Fi unless the user has a specific trusted-LAN reason.
- Remove inbound host ports that are open in the firewall but have no current justified use.
- Keep localhost-only dev services closed to LAN/WAN.
- Router SPI/stateful firewall on.
- Respond to WAN ping off.
- WPS off.
- DMZ off.
- No manual port forwards unless there is a specific known need.
- UPnP acceptable to leave on for console gaming if the user values convenience and the rest of the router posture is sane.
- Remote admin only with guardrails: HTTPS, strong password, custom port if available, source-IP restriction if available, and current firmware.
- Wi‑Fi security at least WPA2-AES; prefer WPA2/WPA3 mixed or WPA3 if all clients support it.
- Guest network optional but useful for visitors/IoT.
- IPv6 may stay on if firewalling is sane; if the user wants simplicity and does not care, leaving it off is acceptable.

## Interpreting Common Findings

### Open host firewall ports with no listener
Treat these as low-effort cleanup items. If a port is allowed but nothing is listening and the user does not recognize it, recommend removing it.

Verification tip:
- Check both runtime and permanent firewalld state before and after cleanup.
- A stale allowance may survive in the permanent config even when nothing is currently listening.

### Open listener on all interfaces but not allowed by firewall
Usually acceptable. Call out that the service is listening broadly, but note that the host firewall still blocks inbound reachability.

Extra interpretation step:
- On Silverblue/Podman-style desktops, a broad listener may belong to a user-level container networking helper such as `pasta` rather than a host daemon.
- Identify the owning process/service before recommending a change; if firewalld is not allowing the port, the practical exposure may still be low.

### UPnP enabled
Do not automatically recommend disabling it for gaming users. Prefer:
- UPnP on
- DMZ off
- no blanket forwards
This is a reasonable middle ground for PS5/Xbox style usage.

### Remote admin enabled
Do not force a disable recommendation if the user explicitly wants it on. Instead, shift to risk reduction:
- HTTPS only
- strong password
- source-IP restriction if supported
- custom external port if supported
- firmware current
- if credentials were shared or typed during the session, recommend rotating the admin password afterward

#### TP-Link AX55 note
On some AX55 firmware builds, the Administration page does not expose a separate WAN HTTP/HTTPS selector or visible web-management-port field in the main form. When that happens:
- treat the missing HTTP option as evidence that remote admin may already be HTTPS-only
- verify by combining live UI inspection with an authoritative TP-Link reference or model-specific forum evidence
- report the conclusion carefully as `appears HTTPS-only on this firmware` rather than overstating what was not directly toggled

## Pitfalls

1. Over-hardening against the user's stated goal.
   - A gaming-focused home user may rationally prefer UPnP on.

2. Treating localhost listeners as exposure.
   - Verify bind addresses before escalating.

3. Missing the difference between router-side and host-side exposure.
   - A service can listen on 0.0.0.0 while still being blocked by host firewall.

4. Ignoring credentials handling.
   - If the session involved router credentials, explicitly recommend rotating the admin password, and often the Wi‑Fi password too.

5. Assuming a consumer router SPA can only be navigated by visible clicks.
   - Some pages are easier to inspect by hash routes or direct DOM/state reads.

## Verification Checklist

- [ ] Host firewall state checked live.
- [ ] Open ports/services compared against active listeners.
- [ ] Router checked for SPI firewall, WAN ping, UPnP, DMZ, forwards, remote admin, WPS, Wi‑Fi security.
- [ ] Recommendations reflect the user's usability/security preference.
- [ ] Any suggested change is distinguished from optional hardening.
- [ ] Credential-rotation advice given if secrets were exposed during review.

## References

- `references/tp-link-archer-ax55-ui-notes.md` — page map, SPA navigation pattern, and AX55-specific Administration/Firewall findings.
- `references/tp-link-archer-ax55-ui-notes.md` — page map and findings patterns for the Archer AX55 web UI.
