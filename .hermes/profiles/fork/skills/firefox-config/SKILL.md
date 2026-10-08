---
name: firefox-config
description: Use when configuring Firefox policies or search defaults.
tags: [firefox, browser, policies, flatpak, linux, windows]
---

# Firefox Configuration

Covers: deploying enterprise policies.json, setting default search engine, resolving correct paths for native RPM vs Flatpak installs on Fedora, and pushing config to Windows via SSH.

## 0. Identify which Firefox is running

Fedora commonly has BOTH a native RPM and a Flatpak Firefox installed simultaneously.

    which firefox           # usually /usr/bin/firefox = RPM
    flatpak list | grep -i firefox
    ps aux | grep firefox | grep -v grep
    # Flatpak process: /app/lib/firefox/firefox (via bwrap)
    # RPM process: /usr/lib64/firefox/firefox
    rpm -q firefox          # confirms RPM install

The process tree is the ground truth -- the running binary determines which policies.json path matters.

## 1. Deploy policies.json

Firefox reads policies.json from a distribution/ subdirectory relative to its install root. Paths differ by install type:

### Native RPM Firefox (Fedora)

System-wide policies path (survives RPM upgrades):

    sudo mkdir -p /etc/firefox/policies/
    sudo cp policies.json /etc/firefox/policies/policies.json

### Flatpak Firefox

Flatpak sandboxes the app -- it ignores /etc/firefox/ by default. Write directly into the Flatpak distribution dir:

    sudo cp policies.json \
      /var/lib/flatpak/app/org.mozilla.firefox/current/active/files/lib/firefox/distribution/policies.json

Pitfall: `sudo tee` with a heredoc fails non-interactively (no tty for password prompt). Use write_file to write the JSON to /tmp first, then `sudo cp /tmp/firefox-policies.json <dest>` -- this pattern works without a tty.

Optionally grant filesystem access for audit purposes:

    flatpak override --user org.mozilla.firefox --filesystem=/etc/firefox/policies:ro

Pitfall: Writing policies.json to the user profile parent dir (~/.var/app/org.mozilla.firefox/config/mozilla/firefox/policies.json) does NOT work for Flatpak Firefox -- Firefox reads policies only from the app install's distribution/ directory. The system Flatpak path (sudo required) is the only writable path that works.

Pitfall: The Flatpak distribution dir is recreated on flatpak update org.mozilla.firefox -- re-deploy policies.json after every Flatpak update.

Pitfall: Fedora does not have crontab by default -- use systemd user timers instead. Create ~/.config/systemd/user/firefox-policy.service (Type=oneshot, ExecStart=redeploy script) and firefox-policy.timer (OnCalendar=daily, Persistent=true, WantedBy=timers.target), then: systemctl --user daemon-reload && systemctl --user enable --now firefox-policy.timer

Pitfall: The redeploy script needs a passwordless sudoers rule for the specific cp command or it will fail silently in the timer context. Write the rule to /etc/sudoers.d/firefox-policy (chmod 440), validated with visudo -c first. To make this automatic: (a) add a passwordless sudoers rule for the specific cp command, (b) schedule a daily/post-update cron that redeploys from /tmp:

    # sudoers rule (one-time, run visudo or write to /etc/sudoers.d/):
    rainbow ALL=(ALL) NOPASSWD: /usr/bin/cp /tmp/firefox-policies.json /var/lib/flatpak/app/org.mozilla.firefox/current/active/files/lib/firefox/distribution/policies.json

    # redeploy script: write JSON to /tmp then sudo cp
    cat > /tmp/firefox-policies.json << 'EOF'
    { ... }
    EOF
    sudo cp /tmp/firefox-policies.json /var/lib/flatpak/.../distribution/policies.json

Pitfall: If both RPM and Flatpak are installed and the running process is the Flatpak (/app/lib/firefox/firefox in ps), deploying only to /etc/firefox/policies/ has no effect on the running browser. Always confirm the running binary first.

### Windows Firefox (via SSH from Linux)

Do not invoke PowerShell over SSH from Linux -- the connection defaults to cmd.exe. Use scp + cmd builtins:

    # 1. scp file to Windows home dir
    scp policies.json admin@192.168.0.181:C:/Users/admin/policies.json

    # 2. SSH with cmd to move into Firefox install
    ssh admin@192.168.0.181 \
      'mkdir "C:\Program Files\Mozilla Firefox\distribution" 2>nul & move "C:\Users\admin\policies.json" "C:\Program Files\Mozilla Firefox\distribution\policies.json" && echo done'

Pitfall: PowerShell cmdlets (New-Item, Set-Content, Out-Null) fail over SSH from Linux -- the shell is cmd.exe, not PowerShell. Use only cmd builtins: mkdir, move, copy, type. Quote paths with spaces using double quotes inside the single-quoted SSH argument.

## 2. Verify

Restart Firefox completely, navigate to about:policies. Policy table should show SearchEngines. Empty table = policies.json not found -- recheck path.

## 3. Brave Search as default

    {
      "policies": {
        "SearchEngines": {
          "Default": "Brave Search",
          "Add": [{
            "Name": "Brave Search",
            "URLTemplate": "https://search.brave.com/search?q={searchTerms}",
            "Method": "GET",
            "IconURL": "https://brave.com/favicon.ico",
            "Alias": "@brave",
            "SuggestURLTemplate": "https://search.brave.com/api/suggest?q={searchTerms}"
          }]
        }
      }
    }

@brave alias: type @brave <query> in address bar to force Brave Search regardless of current default.

## 4. This user's Firefox setup

- Laptop (Fedora): native RPM + Flatpak. Flatpak is the running browser. Active profile: ~/.var/app/org.mozilla.firefox/config/mozilla/firefox/a1f8jsqv.default-release/
- Desktop (192.168.0.181, Win11): native Firefox at C:\Program Files\Mozilla Firefox\. Active profile: 7oi20t52.default-release
- RFP + letterboxing disabled. fingerprintingProtection (ETP) active. Safe browsing + WebRTC off. These are in user prefs -- do not override via policies.json.

## 5. Privacy hardening via user.js

Privacy prefs live in user.js in the active profile dir, NOT in policies.json. policies.json controls enterprise settings (search engine, etc.); user.js controls per-user privacy flags.

Flatpak profile user.js path:

    ~/.var/app/org.mozilla.firefox/config/mozilla/firefox/a1f8jsqv.default-release/user.js

Use write_file to overwrite user.js (execute_code + Path.write_text() also works). Firefox applies user.js on next startup -- restart required.

### Audit workflow

Read prefs.js (runtime state) and user.js (locked overrides) from the active profile, then check specific keys:

    grep -E '(fingerprintingProtection|https_only|geo.enabled|trackingprotection|peerconnection|safebrowsing)' \
      ~/.var/app/org.mozilla.firefox/config/mozilla/firefox/a1f8jsqv.default-release/prefs.js

A pref absent from prefs.js runs at its compiled-in default. Always check the default (MDN or about:config) before concluding it is safe.

### Standing privacy pref set (enforced in user.js)

See references/firefox-privacy-prefs.md for the full annotated set. Key prefs and their correct values for this user:

    media.peerconnection.enabled = false          // WebRTC off (VPN IP leak prevention)
    user_pref("privacy.fingerprintingProtection", true);   // ETP FPP — canvas, fonts, timing, etc.
        privacy.fingerprintingProtection.overrides = "+JSDateTimeUTC,+CanvasRandomization,+EfficientCanvasRandomization,+WebGLRandomization,+WebGLRenderInfo,+WebGLVendorSanitize,+AudioContext,+TouchEvents,+MaxTouchPointsCollapse,+ScreenAvailToResolution,+WindowDevicePixelRatio,+NavigatorHWConcurrency,+NavigatorHWConcurrencyTiered,+FontVisibilityBaseSystem,+ReduceTimerPrecision,+AudioSampleRate"
        // Target names are from RFPTargets.inc (firefox source) — use ONLY these exact strings.
        // Spoof: timezone->UTC (Reykjavik), canvas->randomized, WebGL->Mozilla/Mozilla,
        // HW concurrency->tiered (4 not 8), touch->collapsed to 0, audio->spoofed sample rate.
        // Does NOT include RoundWindowSize (causes letterboxing bars) or ScreenRect/ScreenAvailRect
        // (collapses screen to exact window size, producing a highly unique 1-in-362193 fingerprint).
    browser.safebrowsing.malware.enabled = false  // sends URLs to Google; uBO covers this
    browser.safebrowsing.phishing.enabled = false
    browser.safebrowsing.downloads.enabled = false
    dom.security.https_only_mode = true
    dom.security.https_only_mode_pbm = true       // also apply in private windows
    geo.enabled = false
    geo.provider.network.url = ""
    geo.wifi.scan = false
    privacy.trackingprotection.enabled = true
    privacy.trackingprotection.pbmode.enabled = true   // TP in private windows (default is on; lock it)
    network.dns.disablePrefetch = true
    network.prefetch-next = false
    network.http.speculative-parallel-limit = 0
    browser.send_pings = false
    network.http.sendRefererHeader = 1            // 1 = same-origin only (not 2 = always)
    network.trr.mode = 0                          // use system DNS (VPN-protected); do not override to DoH

Pitfall: privacy.resistFingerprinting is intentionally DISABLED for this user — it causes grey viewport bars regardless of letterboxing sub-pref. Use privacy.fingerprintingProtection (ETP FPP) instead, which covers the same canvas/font/timing protections without the layout side-effect.

Pitfall: fingerprintingProtection.overrides target names must match RFPTargets.inc exactly. Wrong names are silently ignored. Verified working names: JSDateTimeUTC, CanvasRandomization, EfficientCanvasRandomization, WebGLRandomization, WebGLRenderInfo, WebGLVendorSanitize, AudioContext, TouchEvents, MaxTouchPointsCollapse, ScreenAvailToResolution, WindowDevicePixelRatio, NavigatorHWConcurrency, NavigatorHWConcurrencyTiered, FontVisibilityBaseSystem, ReduceTimerPrecision, AudioSampleRate. Check https://raw.githubusercontent.com/mozilla-firefox/firefox/main/toolkit/components/resistfingerprinting/RFPTargets.inc for additions.

Pitfall: Do NOT add +ScreenRect or +ScreenAvailRect to overrides — these collapse the reported screen size to the exact current window size, which is more unique than the real monitor size (1 in 362,000+ vs 1 in 135). Use +ScreenAvailToResolution instead (rounds available screen to resolution).

Pitfall: MaxTouchPoints (collapses to a fixed value) and MaxTouchPointsCollapse (collapses to 0 on non-touch devices) are separate targets. Use MaxTouchPointsCollapse — it resolves the inconsistency where maxTouchPoints=5 but TouchEvent=false.

Pitfall: AudioContext fingerprint value (e.g. 35.749972...) is NOT spoofed by +AudioContext alone in current Firefox FPP — that target controls API availability, not the fingerprint hash. No reliable JS-side fix without RFP. -- a preferences reset or profile corruption can flip it to false. Lock it explicitly.

Pitfall: geo.enabled absent from prefs.js defaults to true. It must be explicitly set false in user.js or location permission prompts are live.

Pitfall: network.http.sendRefererHeader = 0 (never) breaks many legitimate sites. Use 1 (same-origin only) as the privacy-preserving default that does not cause breakage.

### Verification script

After editing user.js, verify all prefs are present with correct values before restarting Firefox.
Run via execute_code (or write to /tmp and run with python3):

    import re, sys
    PROFILE = "/var/home/rainbow/.var/app/org.mozilla.firefox/config/mozilla/firefox/a1f8jsqv.default-release"
    required = {
        "media.peerconnection.enabled": "false",
        "privacy.fingerprintingProtection": "true",
        "browser.safebrowsing.malware.enabled": "false",
        "browser.safebrowsing.phishing.enabled": "false",
        "browser.safebrowsing.downloads.enabled": "false",
        "dom.security.https_only_mode": "true",
        "dom.security.https_only_mode_pbm": "true",
        "geo.enabled": "false",
        "privacy.trackingprotection.enabled": "true",
        "privacy.trackingprotection.pbmode.enabled": "true",
        "network.dns.disablePrefetch": "true",
        "network.trr.mode": "0",
    }
    text = open(f"{PROFILE}/user.js").read()
    fails = []
    for pref, val in required.items():
        pat = rf'user_pref\("{re.escape(pref)}",\s*{re.escape(val)}\)'
        if not re.search(pat, text):
            fails.append(f"FAIL {pref} = {val}")
    if fails:
        for f in fails: print(f)
        sys.exit(1)
    print(f"PASS {len(required)}/{len(required)}")
