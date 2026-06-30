---
name: fedora-atomic-dotfiles-adaptation
description: Adapt third-party Linux dotfiles and ricing setups to Fedora Atomic desktops (Silverblue/Bazzite/Kinoite/Aurora) by treating upstream repos as config sources, not blind installers.
---

# Fedora Atomic Dotfiles Adaptation

## When to use
Use this when the user wants to copy ideas from a dotfiles / ricing repo onto Fedora Atomic variants such as Silverblue, Bazzite, Kinoite, or Aurora, especially for Hyprland, Waybar, Rofi, terminal themes, notification daemons, wallpapers, and related user-space desktop components.

Typical triggers:
- "Will this dotfiles repo work on Silverblue?"
- "Port these Hyprland / Waybar configs to my immutable Fedora setup"
- "Borrow ideas from repo X without running its installer"
- "Implement a themed desktop setup on Atomic Fedora"

## Core principle
On Fedora Atomic, treat upstream dotfiles repos as sources of user-level configuration and assets.

Do:
- Prefer copying and adapting `~/.config` content.
- Back up existing config directories before replacing anything.
- Patch startup commands so missing binaries fail safely.
- Keep machine-specific edits in user override files when the repo supports them.
- Verify installed files on disk after copying and patching.

Do not:
- Blindly run distro installer scripts designed for mutable Fedora or Arch.
- Assume `dnf`, COPR, or system-wide package steps are appropriate for the user's Atomic workflow.
- Preserve author-specific default apps, file managers, monitor names, or wallpaper paths without checking.

## Recommended workflow
1. Inspect the repo before copying.
   - Identify which parts are pure user config (`config/hypr`, `config/waybar`, `config/rofi`, `config/swaync`, terminals, theming assets).
   - Separate them from installer scripts, package managers, system services, or host-specific assumptions.

2. Back up local config first.
   - Save every target config directory to a timestamped backup location under `~/.config/` before modifying anything.
   - For Hyprland-themed desktop work, prefer a fuller "desktop rebuild" snapshot rather than a `~/.config/hypr`-only backup: include adjacent configs like Waybar/Rofi/SwayNC/Wallust, relevant terminal/app configs, wallpaper assets, and `rpm-ostree`/Flatpak manifests.
   - Be explicit about the backup path in the final report.

3. Copy only the selected components.
   - Typical safe targets: terminal config, fastfetch, btop, cava, Hyprland config, Waybar, Rofi, swaync, wlogout, wallpapers, and wallust templates.
   - Keep desktop assets under a user directory such as `~/Pictures/wallpapers/<theme-name>`.

4. Patch for Atomic-safe startup behavior.
   - Disable one-shot bootstrap scripts until dependencies are confirmed.
   - Replace hard startup failures like `exec-once = waybar` with guarded forms such as `sh -lc 'command -v waybar >/dev/null && waybar'`.
   - Comment out advanced shell layers (AGS / Quickshell / similar) unless the user explicitly wants them and the dependencies exist.

5. Patch author-specific defaults.
   - Replace upstream terminal / file-manager defaults with tools actually present in the user's environment.
   - Adjust wallpaper directory variables to the copied asset location.
   - Keep monitor configuration templates, but leave final monitor tuning to the user or a follow-up step.

6. Verify by readback.
   - Confirm key files exist after the copy.
   - Read back patched files to verify the intended lines are present.
   - Check for common breakage such as dangling symlinks in Waybar configs.

7. On Atomic Fedora, discover package names before attempting installs.
   - Use `rpm-ostree install -n ...` first as a dry run to confirm which package names actually exist in the enabled repos.
   - Expect upstream component names and Fedora package names to differ. Example: the `swaync` binary is provided by the Fedora package `SwayNotificationCenter`.
   - If the dry run reports missing packages, use a toolbox with `dnf repoquery` to search exact names and casing before making a real install request.
   - Prefer layering only the runtime pieces that are actually available, then report the remaining compositor/session gaps separately.

8. For Silverblue runtime installation, verify staged-vs-live state explicitly.
   - `rpm-ostree` installs succeed into the next deployment, so binaries will remain missing from `PATH` until reboot.
   - After installation, confirm success with `rpm-ostree status` and tell the user a reboot is required before claiming the tools are installed.

9. If the needed compositor packages are missing from enabled repos, use a COPR-artifact fallback instead of forcing a mutable-repo workflow.
   - First confirm an appropriate Fedora build source exists and inspect its published package names and versions.
   - If adding a repo file under `/etc/yum.repos.d/` is blocked by sudo/password constraints, prefer staging the published RPM artifacts directly with `rpm-ostree` rather than stopping early.
   - Dry-run the exact RPM URLs first to verify dependency resolution.
   - If `rpm-ostree install <https://...rpm>` is flaky on large downloads, download the RPMs locally with `curl -fL --retry ...` and then install the local files via `rpm-ostree install ./pkg.rpm ...`.
   - Report clearly which packages came from Fedora repos versus direct COPR artifacts.

10. When upstream Waybar presets are dependency-heavy, activate a smaller profile first.
   - Reduce the active `~/.config/waybar/config` to core modules such as launcher, workspaces, active window, clock, tray, network, audio, notifications, and power.
   - Remove or defer modules that assume extra services or tools (`weather`, visualizers, update widgets, extra power/profile integrations, custom picker helpers) unless the user explicitly wants them.

## High-value components to port first
Start with the lowest-risk, highest-value user-space components:
- terminal theme/config (Kitty, WezTerm, Ghostty)
- fastfetch
- btop
- cava
- modular Hyprland config structure
- Waybar theme/layout
- Rofi theme/menu config
- swaync
- hyprlock
- wallpapers
- wallust templates

Only port later, and only intentionally:
- AGS
- Quickshell
- package installer scripts
- system integration helpers that assume a specific mutable distro layout

## Hyprland-specific guidance
If the upstream repo is modular, preserve that structure.

Prefer:
- `hyprland.conf` as a thin entrypoint
- `configs/` for upstream defaults
- `UserConfigs/` for local overrides
- `UserScripts/` for user-modified copies of helper scripts
- `monitors.conf` kept separate from the main file

This makes archived or handoff-maintained repos much easier to track or replace later.

## Waybar pitfall
Some repos ship Waybar presets as named files and expect symlinks like `config -> configs/[TOP] Default` and `style.css -> style/[Theme].css`.

When copying manually:
- verify whether those symlinks already exist locally
- if a copy fails through a dangling symlink, remove the broken link first
- either materialize concrete files (`config`, `style.css`) from a chosen preset or recreate valid symlinks intentionally

Always verify that Waybar has no dangling symlinks after installation.

## Wallust guidance
Wallust is a good fit for Atomic desktops because it is user-space theming, but keep the template targets aligned to what you actually copied.

Good practice:
- keep `wallust.toml` trimmed to the installed components
- if the terminal emulator is not installed, do not leave active template targets for it unless harmless
- ensure output directories exist (`~/.config/waybar/wallust`, `~/.config/rofi/wallust`, etc.)

## Reporting requirements
When done, report:
- exactly which config directories were installed
- where backups were written
- which defaults were changed for local safety
- what was verified on disk
- which dependencies are still missing before the setup will actually run

## Verification checklist
- Target directories copied into `~/.config`
- Backup path exists and was reported
- Hyprland startup file patched to avoid hard failures on missing binaries
- Author-specific defaults replaced with local-safe defaults
- Wallust config exists and matches copied components
- Wallpapers copied to the intended user path
- No dangling Waybar symlinks remain

## Support files
- `references/jakoolit-hyprland-dots-silverblue-port.md` — concrete example of porting JaKooLit/Hyprland-Dots into a Fedora Silverblue-safe user-space layout.
- `references/hyprland-runtime-on-silverblue.md` — package-source notes and rpm-ostree artifact-staging fallback for Hyprland runtime installation when host repos lack Hyprland.
- `references/hyprland-desktop-rebuild-backup.md` — what to capture in a reusable Hyprland desktop rebuild snapshot, including wallpapers and rpm-ostree/Flatpak manifests.
