# Firefox RAM Tuning — Fedora Silverblue / Flatpak (FF154, Sep 2026)

Verified knowledge bank from a 3-pass adversarial review session against Firefox 154.0 on Fedora Silverblue 44 + Hyprland/Wayland, 32GB RAM, Intel i5-1145G7 Tiger Lake, Iris Xe GPU.

## Critical Pitfall: Which Profile Is Actually Running?

Firefox may NOT be using the profile at `~/.mozilla/firefox/*.default-release/`.

The running Firefox is determined by the `[Install<hash>]` section in `profiles.ini`, which **overrides** the `Default=1` field in individual `[Profile...]` sections.

**Diagnostic procedure (always run this first):**

```bash
# 1. Find which Firefox binary is running
pgrep -a firefox
# If /app/lib/firefox/firefox: Flatpak instance — profile is via XDG_DATA_HOME

# 2. Find the active profile from the running process environment
cat /proc/$(pgrep -f 'firefox$' | head -1)/environ | tr '\0' '\n' | grep -E 'XDG_DATA_HOME|HOME'

# 3. Read profiles.ini for the Install section (this is the real authority)
cat ~/.mozilla/firefox/profiles.ini | grep -A3 '\[Install'
# Example output:
#   [Install11457493C5A56847]
#   Default=ug6edzeh.1
#   Locked=1
# => Active profile is ug6edzeh.1, not 7pcsz5nm.default-release

# 4. Confirm with the lock file (stale lock = old session, ignore it)
readlink ~/.mozilla/firefox/*/lock 2>/dev/null
# Active lock: points to current machine IP:+PID
# Stale lock: points to old IP or old PID — ignore
```

**Flatpak Firefox profile location:**
- XDG_DATA_HOME is `/var/home/rainbow/.var/app/org.mozilla.firefox/data`
- Profile base: `$XDG_DATA_HOME/mozilla/firefox/`
- BUT: on this machine, Flatpak Firefox binds-mounts `~/.mozilla` directly — `~/.mozilla` IS the profile base
- The active profile is determined by `[Install...]` in `~/.mozilla/firefox/profiles.ini`

## Verified user.js Prefs (FF154, 32GB RAM, Tiger Lake Iris Xe)

All prefs verified against StaticPrefList.yaml, greprefs.js, libxul binary, CacheObserver.cpp, LoginHelper.sys.mjs on Firefox 154.0-5.fc44.

Place user.js in the **active profile directory** (check profiles.ini first).

### High Impact (hundreds of MB)
```js
// Under Fission, webIsolated is the real RAM lever (per-site process cap)
// processCount has minimal effect on its own in FF154
user_pref("dom.ipc.processCount", 4);               // default 8
user_pref("dom.ipc.processCount.webIsolated", 2);   // default 4; saves 200-800MB
```

### Medium Impact (tens of MB)
```js
// HTTP memory cache cap
// CacheObserver formula on 32GB: x=log2(RAM_KB)-14=11; capacity=min(32,poly(x))<<10 = 32768KB
// Setting ABOVE 32768 INCREASES RAM; setting below reduces it
user_pref("browser.cache.memory.capacity", 16384);  // 16MB (auto ceiling = 32MB on 32GB)

// In-memory media cache (audio/video). Default 524288KB (512MB). NOT the video playback buffer.
// YouTube-sized video never uses MemoryBlockCache path; only small in-memory media affected.
user_pref("media.memory_caches_combined_limit_kb", 131072);  // 128MB

// Session undo history — each tab undo stores serialized state in RAM
user_pref("browser.sessionstore.max_tabs_undo", 5);    // default 25
user_pref("browser.sessionstore.max_windows_undo", 1); // default 3
user_pref("browser.sessionstore.interval", 60000);     // default 15000ms; reduces GC pressure
```

### Safety Net / Background Reduction
```js
user_pref("browser.tabs.unloadOnLowMemory", true);                    // default false on desktop; unreliable but harmless
user_pref("browser.tabs.min_inactive_duration_before_unload", 600000); // 10min
user_pref("network.prefetch-next", false);         // privacy + minor RAM
user_pref("network.dns.disablePrefetch", true);    // privacy + minor RAM
user_pref("network.dnsCacheEntries", 800);         // default 1600
user_pref("signon.firefoxRelay.feature", "disabled"); // confirmed value per LoginHelper.sys.mjs
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("app.shield.optoutstudies.enabled", false);
user_pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false);
```

### Hardware Decode (Tiger Lake Iris Xe)
```js
// Tiger Lake (TGLx, device 0x9A49) HAS AV1 8/10-bit HW decode via iHD driver >= 21.x
// Do NOT set media.av1.enabled=false — it forces VP9 SW decode (less efficient)
// force-enabled bypasses the driver blocklist; iHD is stable on Iris Xe
user_pref("media.hardware-video-decoding.force-enabled", true);

// widget.dmabuf.force-enabled: do NOT set on Iris Xe — iHD is NOT on the DMABuf blocklist
// widget.dmabuf.enabled is already true by default on GTK/Wayland
// force-enabled can crash if DMABufDevice::IsEnabled() fails post-blocklist (Bug 1828323)
// Leave dmabuf at default.
```

## Dead / Wrong Prefs to Avoid

| Pref | Status | Notes |
|------|--------|-------|
| `media.ffmpeg.vaapi.enabled` | GONE in FF154 | Replaced by `media.hardware-video-decoding.*` |
| `extensions.pocket.enabled` | GONE in FF2025 | Pocket removed |
| `dom.ipc.forkserver.enable` | Build-flag only | `#ifdef MOZ_ENABLE_FORKSERVER` not set in Fedora release build |
| `dom.suspend_inactive.enabled` | No-op on desktop | Value is `@IS_ANDROID@`, permanently false |
| `dom.screenwakeLock.enabled` | Wrong case | Real pref: `dom.screenwakelock.enabled` (all lowercase) |
| `browser.firefox-view.feature-tour` | Gone in FF154 | Tour feature removed from OnboardingMessageProvider |
| `browser.cache.offline.enable` | GONE in FF154 | AppCache removed |
| `toolkit.telemetry.enabled` | Locked | Official builds lock this; user.js cannot change it |
| `widget.dmabuf.force-enabled` | No-op + crash risk | Iris Xe not blocklisted; default already enabled; force-enabled can crash |
| `media.av1.enabled=false` | Counterproductive | Tiger Lake HAS AV1 HW decode; disabling forces VP9 SW decode |

## GC Tuning — Do Not Touch

GC prefs are a common cargo-cult mistake:
- `javascript.options.mem.gc_allocation_threshold_mb` + lower `gc_high_frequency_time_limit_ms` causes MORE GC scans, not fewer (lower threshold → higher-frequency mode → jank)
- `javascript.options.mem.gc_max_empty_chunk_count` is DEAD in FF154 (removed from StaticPrefList)
- `javascript.options.mem.gc_helper_thread_ratio=0.5` is a type mismatch — pref is integer percent (default 50), not float (0.5 = effectively 0)
- Let Firefox manage GC with its defaults on a 32GB machine

## CacheObserver Formula (32GB verification)

```python
import math
RAM_KB = 32 * 1024 * 1024  # 32GB
x = math.log2(RAM_KB) - 14  # = 11
poly = x*x/3 + x + 2/3      # = 52.0
cap_mb = min(32, poly)       # capped at 32 MB
cap_kb = int(cap_mb) << 10   # = 32768 KB
print(f"Auto ceiling on 32GB: {cap_kb} KB = {cap_mb} MB")
# Output: Auto ceiling on 32GB: 32768 KB = 32 MB
# Any value set ABOVE 32768 INCREASES memory cache RAM vs the auto formula
```

Safe values on 32GB: anything in range [1, 32768]. Value of 16384 saves ~16MB vs auto ceiling.

## Fission Process Architecture (FF154)

Under Fission, web content uses the `webIsolated` process pool:
- `dom.ipc.processCount` controls the legacy/non-Fission content pool (mostly no-op for web RAM)
- `dom.ipc.processCount.webIsolated` controls per-site-origin process count (the real RAM lever)
- They are separate counters; mismatching them cannot crash tabs
- webIsolated=2 means at most 2 isolated processes per origin site (not a global cap of 2 processes)
- Source: ContentParent.cpp `GetMaxProcessCount`

## Adversarial Pass Summary (3 cold grok-4.6 subagents)

- Round 1: Killed 9 dead/wrong prefs (gone prefs, wrong capitalization, no-ops, wrong direction on cache.memory.capacity)
- Round 2: Removed GC prefs (counterproductive, cause jank), confirmed signon.firefoxRelay enum value, confirmed processPrelaunch.fission.number not in FF154
- Round 3: Corrected processCount/webIsolated Fission architecture description; confirmed cache.memory.capacity=16384 has no floor (not clamped by code); confirmed widget.dmabuf.force-enabled is no-op + crash risk on Iris Xe; confirmed media.memory_caches_combined_limit_kb controls only in-memory small-asset cache (not video playback)
