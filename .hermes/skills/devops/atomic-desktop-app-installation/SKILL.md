---
name: atomic-desktop-app-installation
triggers:
  - User says 'install this GitHub app' on Fedora Silverblue or an immutable desktop
  - User says 'set up this Linux desktop app on Silverblue' or Bazzite or Kinoite
  - Need to install a third-party app on an immutable Fedora Atomic system
  - Choosing between Flatpak, toolbox, distrobox, or rpm-ostree for app installation
description: >
  Use when installing third-party Linux desktop apps on Fedora Atomic or similar immutable desktops using the narrowest safe path, favoring user-space staging, desktop integration, and real launch verification.
related_skills:
  - fedora-atomic-dotfiles-adaptation
  - silverblue-system-update-trigger
---

# When to use
Use when the user asks to install a third-party desktop app on Fedora Silverblue, Kinoite, Bazzite, Aurora, or another immutable / Atomic-style Linux desktop.

Typical triggers:
- "install this GitHub app"
- "set up this Linux desktop app on Silverblue"
- "make this AppImage work"
- "add this app to my launcher"
- "install WhatsApp / Discord / Slack / Teams" (or other vendors with weak/no official Linux packaging)

# Goals
1. Prefer the narrowest install path that matches the app's distribution model.
2. Keep system mutation low unless host layering is clearly required.
3. Leave the user with a launchable app, not just a downloaded artifact.
4. Verify launch behavior with real process/runtime evidence before claiming success.

# Core rules
1. Inspect the upstream install surface first: Flatpak, AppImage, `.deb`, RPM, tarball, distro repo, or vendor installer.
2. On Atomic desktops, prefer user-space installation when the app does not need host-level integration.
3. Do not assume an AppImage is runnable as-downloaded; verify FUSE/runtime requirements on the actual host.
4. Separate artifact acquisition, launch-path hardening, and desktop integration.
5. If the vendor's default packaging path is awkward on Atomic, prefer a reversible wrapper script over broad system changes.

# Install-order decision tree
## 1) Choose the narrowest viable source
Preferred order:
1. Flatpak when the app is officially published there and desktop-style sandboxing is acceptable.
2. Native RPM/repo path when host integration is clearly intended and low-risk.
3. AppImage extracted or wrapped in user space when the upstream Linux offering is AppImage-first.
4. Tarball / unpacked binary in user space when the app ships a self-contained archive.
5. `.deb` only as an extraction source or last resort, not the default install path on Fedora Atomic.

## 2) Stage into predictable user-space locations
Good defaults:
- app payloads: `~/Applications/` or `~/.local/opt/<app>/`
- user launchers: `~/.local/bin/<command>`
- desktop entries: `~/.local/share/applications/<app>.desktop`
- copied icons: `~/.local/share/...` or a stable absolute path the desktop entry can reference

Practical rule:
- keep the on-disk layout obvious enough that future updates are mechanical rather than rediscovered.

## 2b) Flatpak first-install workflow (preferred for Flathub desktop apps)
When Flatpak is the chosen path:

1. Discover: `flatpak search <name>` then confirm the app id (e.g. `com.rtosta.zapzap`).
2. Prefer **user** install when the host already has mixed system/user apps and no host integration is required:
   `flatpak install -y --user flathub <app-id>`
3. Prefer system install only when matching an existing system-wide app set or the user asked for multi-user.
4. If `rpm-ostree status` shows `State: busy`, do **not** wait on ostree — Flatpak installs are independent and should proceed.
5. **Large first installs** (new KDE/GNOME Platform runtime + codecs, often 600MB–1GB+) commonly exceed a 300s foreground timeout on home networks. Do not treat exit 124 as failure of the package:
   - Re-run with `terminal(background=true, notify_on_complete=true)` (or a ≥600s timeout if still foreground).
   - Never shell-background with trailing `&` inside the Hermes `terminal` tool — it is rejected; use the tool's `background=true` parameter.
   - Poll/`wait` until `Installation complete.` / exit 0, then verify.
6. Flatpak ships its own `.desktop` under `~/.local/share/flatpak/exports/share/applications/` (user) or `/var/lib/flatpak/exports/...` (system). Do not hand-write a duplicate launcher unless branding/flags require it.
7. Launch: `flatpak run <app-id>`. Verify with `flatpak info <app-id>`, `flatpak ps`, and a 4–5s process-alive check (`pgrep -af <name>` / QtWebEngine/Electron children OK).

### Messaging clients with no official Linux desktop build
Meta/Google/etc. often ship only Web or Windows/macOS binaries. On Atomic, default to a maintained Flathub wrapper rather than inventing AppImage/RPM paths:

| Need | Default Flathub id | Notes |
|------|--------------------|-------|
| WhatsApp | `com.rtosta.zapzap` (ZapZap) | Qt WebEngine WhatsApp Web client; QR link like web.whatsapp.com |
| WhatsApp alt | `com.ktechpit.whatsie`, `io.github.tobagin.karere` | Also Web wrappers; pick one, don't stack three |
| Multi-messenger | Franz / Unify only if user wants multi-service | Heavier; single-purpose client preferred |

Tell the user explicitly: **there is no official WhatsApp Linux app**; the install is a Web wrapper; first launch needs phone QR pairing.

See `references/flatpak-messaging-clients.md` for ids, permissions sketch, uninstall, and **post-install session stability** (logout-on-message, dual tabs, GPU, tray).

### Post-install stability (WhatsApp / ZapZap)
If the user reports logout, QR again, or crash when sending:

1. Load `references/flatpak-messaging-clients.md` § "ZapZap session stability".
2. Privacy first: no chat/IndexedDB content dumps — config, enable flags, sizes, crash logs only.
3. Hardening order (app stopped): single enabled account tab → tray + quit_in_close=false → disable_gpu + software_video_decoding → durable ~/Downloads path → clear GPU caches only → one Web client per number.
4. Do not delete whole `QtWebEngine/` unless the user accepts a full re-pair.

### Permanent login across close / reboot
If the user wants sessions to survive window close or computer restart:

1. Load `references/flatpak-messaging-clients.md` § "Permanent sessions (survive close + reboot)".
2. Conf: `quit_in_close=false`, `tray_icon=true`, `start_background=true`, `start_system=true`, `persistent_cookies=true`.
3. Prefer a single `systemd --user` unit (`flatpak run com.rtosta.zapzap --hideStart`) over double XDG autostart; mark XDG desktop `Hidden=true` if both exist.
4. State limits clearly: phone WhatsApp/WA Business remains **primary**; ZapZap cannot become primary; uninstalling the phone app (or Linked-devices logout) kills the companion; autostart only keeps the link warm.

# AppImage workflow
## 3) Treat AppImage launch as a verification step, not a promise
Workflow:
1. Download the AppImage to a stable user-space path.
2. `chmod +x` it.
3. Try the vendor-supported direct launch or version probe first.
4. If it fails on missing FUSE/runtime support, pivot to extraction rather than reporting the install as done.

**On Fedora Silverblue/Atomic, FUSE (libfuse.so.2) is reliably absent.** The error `dlopen(): error loading libfuse.so.2` is expected — skip straight to `--appimage-extract` rather than treating it as a surprise failure.

## 4) If FUSE is missing, extract instead of widening the host
On Atomic desktops or low-friction user sessions:
1. Run the AppImage with `--appimage-extract`.
2. Treat the extracted `squashfs-root/` as the runtime payload.
3. **Inspect the extracted root before writing the wrapper.** For Electron apps the launch binary is usually named after the app (e.g. `open-whispr`, not `AppRun`). Check `ls squashfs-root/` and look for the `.desktop` file's `Exec=` line as a hint.
4. If `AppRun` mis-resolves paths outside the AppImage runtime, export `APPDIR` explicitly in the wrapper before invoking it.
5. Launch via a user-space wrapper script rather than asking the user to cd into the payload tree.

Practical rule:
- the durable fix is not "install FUSE first"; it is having a working local launch path that survives the current host state.

## 5) Add launch flags only after observing the real failure mode
For Electron/Chromium-style desktop apps, inspect the real stderr/runtime log before guessing flags.
Common classes:
- sandbox constraints -> `--no-sandbox`
- Wayland/Vulkan incompatibility on the current host -> prefer `--ozone-platform=x11` and/or `--disable-vulkan`
- fragile GPU initialization -> use a software-rendering fallback only when needed

Rules:
1. Add only the minimum flags needed to get a stable launch.
2. Keep those flags in the wrapper script, not in a one-off command the user must remember.
3. Verify the app stays running briefly after launch instead of assuming a window appeared.

**For Electron/Chromium GUI apps, `--version` does not exit** — the process stays alive. Verification pattern: launch with a short timeout and treat "process still alive after 4–5 seconds + init log lines visible in stderr" as the success signal. A timeout exit code (124) from the probe is expected, not a failure.

# Desktop integration
## 6) Finish the install with a durable launcher surface
After the runtime path works:
1. Create `~/.local/bin/<command>` as the stable entrypoint.
2. Create a local `.desktop` entry pointing at that wrapper.
3. If the app bundle contains an icon, copy or reference a stable icon path.
4. Avoid fragile relative paths in the `.desktop` file.

Practical rule:
- "installed" means terminal launch and app-launcher launch are both plausible, not just that the binary exists.

# Verification
## 7) Verify proportional to the claim
Before saying the app is installed:
1. Read back the wrapper and `.desktop` files.
2. Confirm permissions on the wrapper.
3. Launch the wrapper in the background.
4. Check whether the process remains alive for a short window or emits a clean version/status signal.
5. If the app logs warnings but stays running, report that distinction clearly.

Good evidence:
- wrapper file content + mode
- `.desktop` file content
- short-lived launch check proving the process stayed up
- explicit note about any non-fatal runtime warnings

## 8) For CLI/TUI tools with heavyweight runtimes, consider a toolbox-backed host wrapper
Use this when the upstream artifact is usable on Linux but wants a toolchain/runtime that you do not want to layer onto the Atomic host.

Pattern:
1. Create or reuse a dedicated Toolbox container for the app runtime.
2. Install the needed runtime/toolchain inside the container.
3. Build or install the app inside a stable path.
4. Expose narrow host-side wrapper scripts in `~/.local/bin/` that `podman exec` into the named container.
5. Pass through the working directory and any required locale/env vars so the wrapped command behaves like a local binary.
6. Verify both the wrapped command itself and the higher-level integration that depends on it.

Use this approach when:
- the user asked for local usability, not necessarily host-global package layering
- the runtime is large or fast-moving (for example Erlang/Elixir/Rust stacks)
- the tool is mostly terminal/headless and desktop launcher integration is not the main need

Rules:
1. Prefer `podman exec` wrappers over nested `toolbox run` wrappers when repeated invocation needs to be stable and low-friction.
2. In Hermes or other non-interactive agent shells, treat `toolbox run` as a probe rather than the final wrapper path; if it throws GLib/GIO or session-init errors, switch to direct `podman exec` wrappers into the named Toolbox container.
3. Preserve the caller's working directory in the wrapper so host-side invocations behave like local binaries.
4. Request `-it` only when stdin/stdout are real TTYs; non-interactive wrappers should fall back to plain `podman exec`.
5. Set locale/encoding env vars in the wrapper when the guest runtime is sensitive to UTF-8 defaults.
6. Keep the wrapper tiny and inspectable; the container name should be explicit, not discovered dynamically on every run.
7. If dependent checks look only for `command -v`, `escript`, or `erl` on the host, provide minimal host wrappers that bridge into the container rather than claiming the tool is unavailable.

# Removing packages on Silverblue/Atomic

## Base OS packages (baked into the image)
These cannot be uninstalled with `rpm-ostree uninstall` — that command only removes layered packages the user added. Base packages require an override:

```bash
sudo rpm-ostree override remove <package>
```

Key points:
- Requires `sudo` — user-level `rpm-ostree` will get `AccessDenied` from DBus.
- Stages the change; takes effect on next reboot.
- Check with `rpm-ostree status` — look for `Removed` under the pending deployment.
- To verify the package is base (not layered): `rpm -q <package>` returning the package without error, combined with `rpm-ostree uninstall` failing with "not currently requested", confirms it is a base package.

## Disable-before-removing pattern for accessibility / system services
For things like screen readers (Orca), disabling via settings is instant; removal requires reboot:

1. Disable immediately (no reboot): `gsettings set org.gnome.desktop.a11y.applications screen-reader-enabled false`
2. Remove permanently: `sudo rpm-ostree override remove orca`
3. Reboot to activate.

Step 1 stops the service from starting in the current session and future sessions; step 2 removes the package from the image overlay so it is gone after reboot.

## Layered packages (user-added)
Use `rpm-ostree uninstall <package>` (sudo optional for your own layered packages; also stages for reboot).

# Common pitfalls
- **Trying `rpm-ostree uninstall` on a base OS package.** It will fail with "not currently requested". Base packages need `sudo rpm-ostree override remove <package>` instead.
- **Skipping `sudo` on `rpm-ostree override remove`.** User-level rpm-ostree gets DBus `AccessDenied` for OS-level operations — always use sudo for override remove.
- treating a successful download as an installation
- assuming AppImage implies FUSE is present; on Silverblue it is reliably absent — go to extraction by default
- **Offering RPM as an easy alternative on Silverblue.** `rpm-ostree install` layers onto the host and requires a reboot. AppImage extraction is lower friction and fully reversible; prefer it unless the user explicitly wants the RPM path.
- editing the extracted payload instead of wrapping it
- forgetting to export `APPDIR` before calling extracted `AppRun`; for Electron apps the binary is usually named after the app (e.g. `open-whispr`), not `AppRun` — check the extracted root
- scattering flags across ad-hoc commands instead of the wrapper
- creating a desktop entry that points at a transient relative path
- **Treating a timed-out `--version` probe as a crash for Electron apps.** These apps don't exit on `--version`; timeout + init logs = success.
- claiming success after a launch attempt that immediately crashes
- using `toolbox run` in wrappers when direct `podman exec` is the more reliable steady-state path, especially from Hermes/non-interactive agent shells where GLib/GIO session-init failures can appear
- fixing the primary app command but forgetting companion runtime probes the integration also checks for
- ignoring locale/encoding warnings from guest runtimes that can be solved in the wrapper
- **Foreground-timing out a first Flatpak install that pulls a new Platform runtime**, then reporting install failed — resume/background the same `flatpak install -y ...` until complete
- **Shell `&` backgrounding inside Hermes `terminal`** for GUI/`flatpak run` probes — use `background=true` instead
- **Promising an "official" WhatsApp/desktop Meta client on Linux** — only Web wrappers exist; say so up front
- **Layering WhatsApp via rpm-ostree or Snap** when Flathub Flatpak already covers it — higher friction, reboot, worse Atomic fit
- **Leaving two ZapZap account tabs enabled** — dual QtWebEngine WA sessions; disable extras in `db/zapzap.db` `users.enable`
- **Treating logout-on-send as only a Meta revoke** — often GPU/QtWebEngine crash or multi-session; fix conf/GPU before full profile wipe
- **Wiping all of `QtWebEngine/` to "fix" logout** — forces QR; clear GPU caches only unless user accepts re-pair
- **Reading WhatsApp chat/IndexedDB content while stabilizing** — forbidden; use config/flags/sizes/crash dumps only
- **Leaving `quit_in_close=true` and tray off** — closing the window kills the linked session cold
- **Editing the wrong Firefox profile** — the profile at `*.default-release/` is often NOT the active one. Flatpak Firefox uses the profile named in the `[Install<hash>]` section of `profiles.ini`, which overrides `Default=1` in individual Profile sections. Always verify: `grep -A3 '\[Install' ~/.mozilla/firefox/profiles.ini`. Also confirm with the running process env: `cat /proc/$(pgrep firefox | head -1)/environ | tr '\0' '\n' | grep XDG_DATA_HOME`. See `references/firefox-ram-tuning.md` for the full diagnostic procedure.
- **Promising ZapZap as primary WhatsApp device** — Meta model is phone-primary only; companions die if phone app is uninstalled or link is revoked
- **Double autostart (XDG + systemd both firing)** — two ZapZap instances; hide XDG or disable one owner
- **Claiming "permanent session" without saying phone-primary limits** — disk + tray + boot start ≠ survive uninstall/revoke
- **Pointing downloads at `/run/user/.../doc/...` portal temps** — use real `~/Downloads` + xdg-download override

# Output expectations
When reporting back to the user:
- state where the payload lives
- state the stable launch command/path
- mention any wrapper flags added and why
- distinguish hard blockers from non-fatal warnings
- include the exact verification evidence used

## Flatpak transient update errors (non-blocking)

During system update runs, these Flatpak errors are safe to ignore:

**Chromium SSL/CDN fetch failure** (curl 56 / curl 35):
- Cause: transient Flathub CDN/TLS blip. Network is healthy; the `.filez` object hash doesn't change between retries in the same session.
- Resolution: self-resolves by next daily run. Report: "Chromium not updated — transient Flathub SSL error. Will retry automatically."

**System Flatpak "No such ref" bulk warnings**:
- Pattern: `Warning: Treating remote fetch error as non-fatal since <ref> is already installed: No such ref 'runtime/org.gnome.Platform/x86_64/50'`
- All are marked non-fatal; actual app updates proceed after the warning block.
- How to report: ignore in summary — only report actual app-level success/failure.

**Reboot notification "already loaded"**:
- `Failed to start transient service unit: Unit reboot-required-notify.service was already loaded or has a fragment file.`
- Benign. A prior run queued the notification. Reboot IS required; script exits non-zero but the requirement is real.

See `references/flatpak-transient-errors.md` for observed examples (Aug 2026: Chromium curl 56/35, 25+ no-such-ref warnings).

# Supporting references
- `references/appimage-fuse-extract-wrapper.md` — extracted-AppImage pattern for immutable desktops, including `APPDIR` wrapper export, desktop entry integration, and short-window launch verification
- `references/toolbox-backed-cli-runtime-wrappers.md` — host-visible wrappers into a dedicated Toolbox/Podman runtime for CLI/TUI apps that need heavyweight runtimes on Atomic desktops
- `references/flatpak-transient-errors.md` — non-blocking Flatpak update error patterns: Chromium SSL/CDN fetch failures, system "No such ref" bulk warnings, reboot-notification "already loaded" message
- `references/flatpak-messaging-clients.md` — WhatsApp/other messenger Flatpak defaults on Atomic (ZapZap ids, user install, QR pairing, large-runtime timeout handling, logout/session stability, privacy boundary)
- `references/firefox-ram-tuning.md` — Verified Firefox 154 RAM tuning knowledge bank: active profile detection (profiles.ini `[Install...]` always wins), CacheObserver formula, 17 evidence-graded prefs for 32GB/Tiger Lake/Iris Xe, dead pref list, GC anti-patterns, 3-pass adversarial review summary.

# Overlap note
This overlaps with broader Fedora Atomic adaptation skills. Keep this skill focused on third-party desktop app installation and launcher integration rather than dotfiles/ricing or repo-specific packaging work.
