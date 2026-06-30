# Hyprland runtime on Fedora Silverblue / Atomic

Use this when the config port is done but Fedora Atomic host repos do not provide the needed Hyprland compositor stack.

## Proven pattern
1. Install whatever runtime pieces are available from enabled Fedora repos with `rpm-ostree install -n ...` first to confirm names.
2. Distinguish repo package names from binary names. Example from this session:
   - binary `swaync` came from package `SwayNotificationCenter`
   - `rofi` was available as package `rofi`
   - `waybar`, `cliphist`, `cava`, `fastfetch`, `brightnessctl` were available directly
3. Verify staged success with `rpm-ostree status`; do not claim binaries are usable before reboot.
4. If Hyprland is absent from the enabled repos, inspect a Fedora-targeted build source and confirm exact artifact URLs and versions.
5. If adding a COPR repo file requires sudo the session cannot supply, stage the RPM artifacts directly instead.

## Direct artifact fallback
When `rpm-ostree install https://...rpm` is unreliable on large files, use:
- `curl -fL --retry 5 --retry-delay 2 -O <url>` to download locally first
- then `rpm-ostree install ./hyprland.rpm ./hypridle.rpm ./hyprlock.rpm ./xdg-desktop-portal-hyprland.rpm ...`

This avoided a truncated-body failure on a large Hyprland RPM and succeeded once the files were local.

## Session-specific validated source
AshBuk Hyprland Fedora packaging was validated as a Fedora 44 source for:
- `hyprland`
- `hypridle`
- `hyprlock`
- `xdg-desktop-portal-hyprland`

The source advertised Fedora 43/44 support and produced a successful `rpm-ostree` dependency resolution and staged deployment on Silverblue 44.

## Reporting checklist
- Separate Fedora-repo layered packages from local/COPR-artifact packages.
- Say explicitly that activation waits until reboot.
- If some optional pieces remain missing (`swww`, `wallust`, `wezterm`, `hyprsunset` in this session), report them as remaining gaps, not as reasons to block the core Hyprland stack.

## When Hyprland suddenly disappears after an upgrade
If the user reports a "Hyprland failure" after an rpm-ostree cleanup or upgrade, first distinguish config breakage from package removal:
- `rpm-ostree status` — compare current vs previous deployment `LocalPackages`
- `find /usr/share/wayland-sessions -maxdepth 1 -type f | grep -i hypr` — if no Hyprland desktop entry exists, GDM cannot launch Hyprland regardless of config quality
- confirm whether the current session fell back to GNOME (`XDG_CURRENT_DESKTOP=GNOME`, `DESKTOP_SESSION=gnome`)

Treat a missing Hyprland session entry as a packaging/deployment problem, not a dotfiles problem. In that case, stage the compositor stack back into the next deployment from verified local RPMs or the validated COPR artifacts before spending time on config debugging.
