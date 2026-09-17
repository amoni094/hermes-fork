# Flatpak messaging clients on Fedora Atomic

## WhatsApp (no official Linux app)

Meta does not ship a native WhatsApp desktop for Linux. Desktop options are WhatsApp Web wrappers.

### Default (validated 2026-08-26, Silverblue 44)

```bash
flatpak search whatsapp
flatpak install -y --user flathub com.rtosta.zapzap
flatpak run com.rtosta.zapzap
```

| Field | Value |
|-------|--------|
| Name | ZapZap |
| App id | `com.rtosta.zapzap` |
| Version seen | 7.4.2 |
| Runtime | `org.kde.Platform//6.11` (large first pull) |
| Install scope | `--user` preferred |
| Desktop file | `~/.local/share/flatpak/exports/share/applications/com.rtosta.zapzap.desktop` |
| License | GPL-3.0-or-later |
| Config | `~/.var/app/com.rtosta.zapzap/config/ZapZap/ZapZap.conf` |
| Data | `~/.var/app/com.rtosta.zapzap/data/ZapZap/` |
| Accounts DB | `~/.var/app/com.rtosta.zapzap/data/ZapZap/db/zapzap.db` (table `users`) |
| WebEngine profiles | `.../data/ZapZap/QtWebEngine/<profile>/` |

Permissions sketch (inform user, do not widen casually): network, wayland/x11, pulseaudio, devices; filesystem: xdg-documents, xdg-download, xdg-pictures; notifications D-Bus.

First-run UX: QR code → phone WhatsApp → Linked devices (same as web.whatsapp.com).

### Alternatives (Flathub)

- `com.ktechpit.whatsie` — Whatsie (Qt WebEngine)
- `io.github.tobagin.karere` — Karere
- Multi-service: Franz (`com.meetfranz.Franz`), Unify — only if user wants multi-messenger

Pick **one** WhatsApp client. Do not install several wrappers side by side unless comparing.

### Uninstall

```bash
flatpak uninstall --user com.rtosta.zapzap
# optional: flatpak uninstall --user --unused
```

## Privacy boundary (mandatory while stabilizing)

When fixing logout/crash/session issues on a personal WhatsApp wrapper:

- Do **not** open chats, read message bodies, dump IndexedDB/Local Storage contents, or restore purged personal session content.
- Allowed evidence: app config, process/flatpak status, crash dumps, log lines that are not message text, **sizes/counts** of storage files, account-tab enable flags, cookie **counts** (not values), phone Linked-devices advice.
- User memory may forbid retrieving/restoring WhatsApp personal session content — honor that even if the user asks to "fix the session" in a way that implies reading chats.

## ZapZap session stability (logout / QR again / dies on send)

Validated hardening path on Fedora Atomic + Wayland + Intel Iris Xe (2026-08-28). Symptom: "logged out as soon as I messaged" often means QtWebEngine crash/session wipe or multi-session conflict, not necessarily Meta deliberately revoking the link mid-type.

### Diagnose (app closed preferred)

```bash
flatpak kill com.rtosta.zapzap 2>/dev/null || true
# config
cat ~/.var/app/com.rtosta.zapzap/config/ZapZap/ZapZap.conf
# account tabs (enable flags only)
python3 - <<'PY'
import sqlite3
c=sqlite3.connect('/var/home/rainbow/.var/app/com.rtosta.zapzap/data/ZapZap/db/zapzap.db')
print(list(c.execute('select id,name,enable from users')))
PY
# profile footprint (sizes only — no content dumps)
du -sh ~/.var/app/com.rtosta.zapzap/data/ZapZap/QtWebEngine/* 2>/dev/null
ls -la ~/.var/app/com.rtosta.zapzap/data/ZapZap/crash-dumps/ 2>/dev/null
# competing Web clients
flatpak ps; pgrep -af 'whatsapp|ZapZap|zapzap' || true
```

Note: root `.../data/ZapZap/zapzap.db` may be empty; real accounts live under `.../data/ZapZap/db/zapzap.db` with table `users` (not legacy `accounts`).

### Common failure modes

| Mode | Evidence | Fix |
|------|----------|-----|
| Dual account tabs | `users` has two+ rows with `enable=1`; two QtWebEngine profile dirs (`storage-whats`, `2`, …) | Keep **one** enabled tab: `UPDATE users SET enable=0 WHERE id!=1` (adjust id). Two WA Web sessions for same/linked numbers fight each other. |
| Quit-on-close + no tray | `system/quit_in_close=true`, `system/tray_icon=false` | Set `quit_in_close=false`, `tray_icon=true` so close hides to tray (`keep_running_in_background = not quit_in_close`). |
| GPU / media crash | Known ZapZap issues around QtWebEngine media; sudden exit while sending/opening media | Set `performance/disable_gpu=true`, `performance/software_video_decoding=true`. Clear **GPU caches only** (see below). |
| Background throttle | Default `web/background_throttling=true` | Set `web/background_throttling=false` so tray/hidden session stays warm. |
| Transient download path | `system/download_path=/run/user/.../doc/...` (portal temp) | Point at real `~/Downloads`; `flatpak override --user com.rtosta.zapzap --filesystem=xdg-download:create`. |
| Competing browser WA Web | Firefox/Chrome also on web.whatsapp.com for same number | Close browser WA Web; one desktop link per number. |
| Wayland Qt path | Session is Wayland; ZapZap defaults to **xcb** unless `system/wayland=true` | Leave `wayland=false` (xcb) unless a known GPU (e.g. some NVIDIA) needs native Wayland. |

### Stable ZapZap.conf keys (merge into existing file; backup first)

Preserve existing `geometry=`, `windowState=`, and `spellCheckLanguages=@Variant(...)` lines. Minimum stability block:

```ini
[performance]
auto_gpu_workaround=true
cache_type=DiskHttpCache
disable_gpu=true
in_process_gpu=false
js_memory_limit_index=2
js_memory_limit_mb=1024
persistent_cookies=true
process_per_site=true
single_process=false
software_rendering=false
software_video_decoding=true

[system]
quit_in_close=false
tray_icon=true
wayland=false
download_path=/var/home/USER/Downloads

[web]
background_throttling=false
```

ZapZap reads these via its SettingsManager / SetupManager (`--disable-gpu`, `--disable-accelerated-video-decode`, etc.). Do not fight them with random `flatpak override --env=QTWEBENGINE_CHROMIUM_FLAGS=...` unless conf cannot stick.

### Safe cache clear (does not wipe login by design)

```bash
# ONLY GPU/shader caches — keep Cookies, IndexedDB, Local Storage, Service Worker
base=~/.var/app/com.rtosta.zapzap/data/ZapZap/QtWebEngine
for d in "$base"/*/GPUCache "$base"/*/DawnWebGPUCache "$base"/*/DawnGraphiteCache \
         "$base"/*/ShaderCache "$base"/*/GrShaderCache "$base"/*/GraphiteDawnCache; do
  [ -d "$d" ] && rm -rf "$d"
done
```

Never "fix logout" by deleting whole `QtWebEngine/` unless the user accepts a full QR re-pair.

### After hardening

1. `flatpak run com.rtosta.zapzap`
2. If QR appears, session was already dead — one fresh pair is OK.
3. Phone: WhatsApp → Linked devices — prune stale Web/ZapZap entries; keep one.
4. Prefer window close (tray) over Quit.
5. Do not run web.whatsapp.com in a browser for the same number at the same time.

### Permanent sessions (survive close + reboot)

User ask shape: "make chat sessions permanent / keep login after close / restart computer."

**What is durable on disk (already true if profile intact):**
- Login lives under `~/.var/app/com.rtosta.zapzap/` (Cookies, Local Storage, IndexedDB). Closing the app does **not** wipe it unless QtWebEngine crashes mid-write or the whole profile is deleted.
- Closing the window only stays warm if `quit_in_close=false` + `tray_icon=true` (process stays in tray). Full Quit from tray still keeps on-disk login; reopen should not need QR if Meta still accepts the link.

**What still requires the phone (cannot be fixed in ZapZap conf):**
- WhatsApp/WhatsApp Business on the phone is always the **primary** device. ZapZap is a **companion** (same as web.whatsapp.com / official Desktop). There is **no** way to make ZapZap primary.
- Uninstalling WhatsApp/WA Business on the phone effectively kills linked companions for that number (ZapZap will disconnect / demand QR). Uninstall ≠ delete account; reinstall + verify number usually invalidates old links — re-scan.
- Long phone inactivity can still revoke all companions server-side. Autostart only reduces cold offline time; it does not replace the primary phone registration.
- Logging out a device from phone **Linked devices** is the intentional way to kill ZapZap without uninstalling the phone app.

**Boot / login warm-start (validated pattern 2026-08-28):**

1. Conf extras (merge; preserve geometry/windowState/spellcheck):
   ```ini
   [system]
   start_background=true
   start_system=true
   quit_in_close=false
   tray_icon=true
   ```
2. Prefer **one** owner of autostart — user systemd unit, not double-launch with XDG:
   - Unit: `~/.config/systemd/user/zapzap.service`
   ```ini
   [Unit]
   Description=ZapZap WhatsApp (background after login)
   After=graphical-session.target
   PartOf=graphical-session.target

   [Service]
   Type=simple
   ExecStart=/usr/bin/flatpak run com.rtosta.zapzap --hideStart
   Restart=on-failure
   RestartSec=10

   [Install]
   WantedBy=default.target
   ```
   - Enable: `systemctl --user daemon-reload && systemctl --user enable --now zapzap.service`
   - Status/off: `systemctl --user status zapzap.service` / `systemctl --user disable --now zapzap.service`
3. If ZapZap also wrote `~/.config/autostart/com.rtosta.zapzap.desktop`, set `Hidden=true` (or remove) so XDG + systemd do not start two instances.
4. CLI flag note: app supports `--hideStart` / background start via conf `start_background`; do not invent random Chromium flags for "stay logged in."
5. Dedup conf keys after edits — QSettings `.conf` with duplicate keys (e.g. two `geometry=`) confuses reads; keep one of each key per section.

**User-facing honesty checklist:**
- Yes: tray close + disk profile + boot autostart ≈ "stays logged in across close/reboot."
- No: ZapZap as primary; survive uninstalling the phone app; survive phone Linked-devices logout; infinite offline without primary.
- Prefer spare/old phone left on Wi-Fi if they want a "desktop-first" feel — still phone-primary.

### Upstream signals (context, not required reading every time)

- Multi-device / sudden QR: ZapZap issues around accounts logged out (e.g. #653 class).
- Media/GPU abort: QtWebEngine media path crashes reported on recent ZapZap (e.g. #866 class).

## Large first-install / Hermes terminal notes

First install of ZapZap pulled KDE Platform + GL/codecs (~hundreds of MB). On a ~0.5–1 MB/s link, a 300s foreground `flatpak install` hit exit 124 mid-runtime download. Same command continued cleanly with:

- `terminal(background=true, notify_on_complete=true)`
- wait/poll until `Installation complete.` and exit 0

Do not use shell trailing `&` inside Hermes `terminal` for `flatpak run` verification — tool rejects it; pass `background=true`.

Launch verification that worked:

```bash
flatpak info com.rtosta.zapzap
# background: flatpak run com.rtosta.zapzap
sleep 5
pgrep -af 'zapzap|ZapZap'
flatpak ps | rg -i zap
```

Alive `python /app/bin/zapzap` + `QtWebEngineProcess` children = success.

## When not to use this path

- User explicitly wants browser-only: pin https://web.whatsapp.com — no Flatpak needed
- User wants host-layered RPM: discourage on Atomic unless they accept reboot/`rpm-ostree`
- Snap: avoid as default on Silverblue when Flathub already has the app
