---
name: firefox-privacy-hardening
description: Use when hardening Firefox fingerprinting/privacy on Linux.
---

# Firefox Privacy Hardening (Flatpak, Linux)

## Profile path

    ~/.var/app/org.mozilla.firefox/config/mozilla/firefox/a1f8jsqv.default-release/user.js

## Testing sites (open all, paste results back)

    coveryourtracks.eff.org/kcarter?incremental=1
    browserleaks.com/canvas
    browserleaks.com/javascript
    browserleaks.com/webgl
    mullvad.net/en/check
    www.deviceinfo.me

## Design decisions

- privacy.resistFingerprinting DISABLED — causes grey viewport bars regardless of letterboxing sub-pref
- fingerprintingProtection (ETP FPP) used instead with explicit RFPTargets.inc overrides
- CanvasBlocker extension handles AudioContext and screen spoofing
- WebRTC fully disabled (no video calls in use)
- Safe browsing disabled (sends URLs to Google; uBlock covers it)
- network.trr.mode=0 — system DNS used (protected by VPN + dnscrypt-proxy)

## Verified final user.js (2026-10-05)

```
// Firefox Flatpak — privacy hardening
// resistFingerprinting DISABLED: causes grey bars. ETP FPP covers canvas, timing, WebGL.

// Telemetry off
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("app.shield.optoutstudies.enabled", false);
user_pref("app.normandy.enabled", false);
user_pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false);
user_pref("toolkit.telemetry.enabled", false);
user_pref("toolkit.telemetry.unified", false);
user_pref("browser.ping-centre.telemetry", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);

// WebRTC — fully disabled
user_pref("media.peerconnection.enabled", false);

// Fingerprinting — ETP FPP with explicit RFPTargets.inc overrides
// Source: https://raw.githubusercontent.com/mozilla-firefox/firefox/main/toolkit/components/resistfingerprinting/RFPTargets.inc
user_pref("privacy.fingerprintingProtection", true);
user_pref("privacy.fingerprintingProtection.overrides",
  "+JSDateTimeUTC,+CanvasRandomization,+EfficientCanvasRandomization,+WebGLRandomization,+WebGLRenderInfo,+WebGLVendorSanitize,+AudioContext,+ScreenAvailToResolution,+WindowDevicePixelRatio,+NavigatorHWConcurrency,+NavigatorHWConcurrencyTiered,+FontVisibilityBaseSystem,+ReduceTimerPrecision,+AudioSampleRate");
// NOT included: RoundWindowSize (letterboxing bars), NavigatorUserAgent (breaks sites),
// TouchEvents (locks maxTouchPoints to 5), MaxTouchPointsCollapse (same problem)

// Safe browsing — disabled
user_pref("browser.safebrowsing.malware.enabled", false);
user_pref("browser.safebrowsing.phishing.enabled", false);
user_pref("browser.safebrowsing.downloads.enabled", false);

// HTTPS-only
user_pref("dom.security.https_only_mode", true);
user_pref("dom.security.https_only_mode_pbm", true);

// Geolocation
user_pref("geo.enabled", false);
user_pref("geo.provider.network.url", "");
user_pref("geo.wifi.scan", false);

// Tracking protection
user_pref("privacy.trackingprotection.enabled", true);
user_pref("privacy.trackingprotection.pbmode.enabled", true);

// Referer / pings
user_pref("network.http.sendRefererHeader", 1);  // same-origin only
user_pref("browser.send_pings", false);

// Network
user_pref("network.trr.mode", 0);                                 // system DNS
user_pref("network.http.speculative-parallel-limit", 0);
user_pref("browser.places.speculativeConnect.enabled", false);
user_pref("network.prefetch-next", false);
user_pref("network.dns.disablePrefetch", true);
user_pref("network.captive-portal-service.enabled", false);
user_pref("network.connectivity-service.enabled", false);

// userChrome
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
```

## CanvasBlocker extension settings

Install: https://addons.mozilla.org/en-US/firefox/addon/canvasblocker/
Version tested: 1.12 (Feb 2026)

Settings (Expert Mode on):
- Block mode: fake (not block)
- Canvas 2D: OFF (ETP FPP handles it)
- WebGL: OFF (ETP FPP handles it)
- Audio API: ON — fake readout, noise: minimal, non-persistent RNG, use audio cache: ON
- DOMRect API: ON
- Screen API: ON (spoofs to non-real resolution per session)
- Navigator: OFF (breaks sites)
- History: OFF
- RNG: non-persistent (changes per Firefox restart)

## Pitfalls

- TouchEvents FPP target locks maxTouchPoints to 5 even if dom.maxtouchpoints=0 is set — remove it
- MaxTouchPointsCollapse also leaves maxTouchPoints at 5 — remove it too
- dom.maxtouchpoints pref does NOT affect navigator.maxTouchPoints in JS — only RFP does
- ScreenRect/ScreenAvailRect/WindowOuterSize collapse screen to actual window size — 18+ bits, worse than nothing; remove them
- ScreenSize is NOT a valid RFPTargets.inc name — correct names are ScreenRect, ScreenAvailRect (but avoid, see above)
- JSDateTimeUTC is correct for timezone (not "Timezone")
- AudioContext FPP target does not spoof the hash value, only API availability — use CanvasBlocker for audio
- fingerprintingProtection + CanvasBlocker coexist fine
- Canvas "100% unique" on EFF DB just means randomized hash not seen before — not a real problem if it changes per domain/session
- FxA NS_ERROR_UNKNOWN_HOST errors in console are harmless — expected when FxA endpoints are stubbed out

## Verified results (2026-10-05)

    Timezone:           Atlantic/Reykjavik UTC+0 — 2.74 bits (was 11.12)
    Canvas:             randomized by first party domain — 0.93 bits
    WebGL hash:         randomized by first party domain — 1.02 bits
    WebGL vendor:       Mozilla~Mozilla — 3.71 bits (was Intel~Intel 6.48)
    AudioContext:       randomized by first party domain — 1.35 bits (was 2.25 stable)
    Screen:             spoofed via CanvasBlocker (changes per restart)
    HW concurrency:     4 spoofed from 8
    Device memory:      hidden
    WebRTC:             disabled
    Geolocation:        blocked
    LAN IP:             hidden
    GPU identity:       hidden
    VPN:                not flagged as VPN by deviceinfo.me

    Residuals (accept, unfixable without RFP):
    maxTouchPoints:     5 with TouchEvent=false — 4.35 bits, 1 in 20 browsers
    Font set:           Arial/Calibri/etc — 6.68 bits, JS probing bypasses CSS restrictions
    User agent:         Firefox 157 Linux x86_64 — 7.57 bits

## DNS / VPN stack

    VPN:            ProtonVPN WireGuard (proton0)
    DNS:            dnscrypt-proxy (127.0.2.1) -> Cloudflare/Quad9 DoH through VPN tunnel
    IPv6:           blocked (Proton leak-protection dummy interface)
    Blocklist:      73,645 domains, daily auto-update via systemd timer
    Verification:   dig telemetry.nvidia.com @127.0.2.1 -> locally blocked

## Verification script

```python
import re, sys
path = '/var/home/rainbow/.var/app/org.mozilla.firefox/config/mozilla/firefox/a1f8jsqv.default-release/user.js'
c = open(path).read()
checks = [
    ('fingerprintingProtection=true',   r'privacy\.fingerprintingProtection",\s*true'),
    ('JSDateTimeUTC in overrides',       'JSDateTimeUTC'),
    ('CanvasRandomization in overrides', 'CanvasRandomization'),
    ('WebGLRenderInfo in overrides',     'WebGLRenderInfo'),
    ('NO TouchEvents in overrides',      lambda c: '+TouchEvents' not in c),
    ('NO MaxTouchPointsCollapse',        lambda c: 'MaxTouchPointsCollapse' not in c),
    ('NO +ScreenRect',                   lambda c: '+ScreenRect' not in c),
    ('WebRTC disabled',                  r'media\.peerconnection\.enabled",\s*false'),
    ('geo.enabled=false',                r'geo\.enabled",\s*false'),
    ('https_only_mode=true',             r'https_only_mode",\s*true'),
    ('trackingprotection=true',          r'trackingprotection\.enabled",\s*true'),
    ('dns disablePrefetch=true',         r'disablePrefetch",\s*true'),
]
ok = 0
for name, pat in checks:
    hit = pat(c) if callable(pat) else bool(re.search(pat, c))
    print('PASS' if hit else 'FAIL', name)
    ok += hit
print(f'ad-hoc verification: {ok}/{len(checks)}')
```
