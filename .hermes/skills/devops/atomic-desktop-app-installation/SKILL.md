---
name: atomic-desktop-app-installation
description: Install third-party Linux desktop apps on Fedora Atomic or similar immutable desktops using the narrowest safe path, favoring user-space staging, desktop integration, and real launch verification.
---

# When to use
Use when the user asks to install a third-party desktop app on Fedora Silverblue, Kinoite, Bazzite, Aurora, or another immutable / Atomic-style Linux desktop.

Typical triggers:
- "install this GitHub app"
- "set up this Linux desktop app on Silverblue"
- "make this AppImage work"
- "add this app to my launcher"

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

# AppImage workflow
## 3) Treat AppImage launch as a verification step, not a promise
Workflow:
1. Download the AppImage to a stable user-space path.
2. `chmod +x` it.
3. Try the vendor-supported direct launch or version probe first.
4. If it fails on missing FUSE/runtime support, pivot to extraction rather than reporting the install as done.

## 4) If FUSE is missing, extract instead of widening the host
On Atomic desktops or low-friction user sessions:
1. Run the AppImage with `--appimage-extract`.
2. Treat the extracted `squashfs-root/` as the runtime payload.
3. If `AppRun` mis-resolves paths outside the AppImage runtime, export `APPDIR` explicitly in the wrapper before invoking it.
4. Launch via a user-space wrapper script rather than asking the user to cd into the payload tree.

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

# Common pitfalls
- treating a successful download as an installation
- assuming AppImage implies FUSE is present
- editing the extracted payload instead of wrapping it
- forgetting to export `APPDIR` before calling extracted `AppRun`
- scattering flags across ad-hoc commands instead of the wrapper
- creating a desktop entry that points at a transient relative path
- claiming success after a launch attempt that immediately crashes
- using `toolbox run` in wrappers when direct `podman exec` is the more reliable steady-state path, especially from Hermes/non-interactive agent shells where GLib/GIO session-init failures can appear
- fixing the primary app command but forgetting companion runtime probes the integration also checks for
- ignoring locale/encoding warnings from guest runtimes that can be solved in the wrapper

# Output expectations
When reporting back to the user:
- state where the payload lives
- state the stable launch command/path
- mention any wrapper flags added and why
- distinguish hard blockers from non-fatal warnings
- include the exact verification evidence used

# Supporting references
- `references/appimage-fuse-extract-wrapper.md` — extracted-AppImage pattern for immutable desktops, including `APPDIR` wrapper export, desktop entry integration, and short-window launch verification
- `references/toolbox-backed-cli-runtime-wrappers.md` — host-visible wrappers into a dedicated Toolbox/Podman runtime for CLI/TUI apps that need heavyweight runtimes on Atomic desktops

# Overlap note
This overlaps with broader Fedora Atomic adaptation skills. Keep this skill focused on third-party desktop app installation and launcher integration rather than dotfiles/ricing or repo-specific packaging work.
