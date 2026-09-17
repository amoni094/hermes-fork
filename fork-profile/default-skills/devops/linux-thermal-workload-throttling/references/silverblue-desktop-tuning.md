# Fedora Silverblue 44 Desktop Tuning — Validated Config (Sep 2026)

System: ThinkPad i5-1145G7, 32GB RAM, NVMe btrfs, Hyprland/GDM, ProtonVPN+Tailscale

## /etc/sysctl.d/99-desktop-perf.conf (complete, final)

```
vm.vfs_cache_pressure = 35
fs.inotify.max_user_instances = 512
net.ipv4.tcp_fastopen = 1
vm.compaction_proactiveness = 0
vm.watermark_boost_factor = 1
vm.watermark_scale_factor = 125
vm.dirty_ratio = 20
```

## /etc/sysctl.d/99-swappiness.conf (keep separate to avoid ordering conflict)

```
vm.swappiness = 10
```

Rationale for separation: both files start with 99-, so load order is alphabetical between them.
`99-swappiness.conf` sorts AFTER `99-desktop-perf.conf`, so any key duplicated in
99-swappiness.conf silently wins. Keeping only swappiness there avoids the conflict.

## Verified live values post-apply

All confirmed by `sysctl -n <key>`:

| Key | Value |
|-----|-------|
| vm.vfs_cache_pressure | 35 |
| vm.swappiness | 10 |
| vm.compaction_proactiveness | 0 |
| vm.watermark_boost_factor | 1 |
| vm.watermark_scale_factor | 125 |
| fs.inotify.max_user_instances | 512 |
| net.ipv4.tcp_fastopen | 1 |
| vm.dirty_ratio | 20 |

## Services

| Service | State | Reason |
|---------|-------|--------|
| cups.service | disabled | no printers |
| cups.socket | disabled | no printers |
| ModemManager.service | disabled | modem unused (WWAN radio blocked separately) |
| switcheroo-control.service | disabled | single GPU |
| tuned-ppd.service | **masked** | D-Bus activation path; disable alone insufficient |
| tuned.service | enabled, active | sole power manager |
| thermald.service | active | polling mode, --ignore-cpuid-check drop-in |

## Thermald drop-in

`/etc/systemd/system/thermald.service.d/ignore-cpuid.conf`:
```ini
[Service]
ExecStart=
ExecStart=/usr/sbin/thermald --no-daemon --ignore-cpuid-check --dbus-enable --adaptive --systemd
```

The double ExecStart= (blank first) clears the inherited Exec before setting the new one.

## WWAN radio block

```bash
sudo rfkill block wwan
echo 0 | sudo tee /sys/devices/platform/thinkpad_acpi/wwan_enable
```

`/etc/udev/rules.d/70-wwan-disable.rules`:
```
ACTION=="add", SUBSYSTEM=="net", KERNEL=="wwan0", RUN+="/usr/sbin/rfkill block wwan"
```

Note: wwan_enable sysfs write does NOT survive reboot (ephemeral). systemd-rfkill.service
persists the rfkill state; the udev rule re-applies on hotplug. Together they are sufficient.

## NVMe / btrfs scheduler

```
/sys/block/nvme0n1/queue/scheduler: none (correct for NVMe; no explicit change needed)
btrfs mount opts: zstd,ssd,discard=async (in /etc/fstab)
```

## tuned desktop profile

Active: `desktop` (via `tuned-adm profile desktop`)
Verify: `tuned-adm active` -> Current active profile: desktop
Adds: `kernel.sched_autogroup_enabled = 1` on top of balanced.

## EPP / governor

governor: powersave (managed by tuned desktop profile)
EPP: balance_performance (set by EPP lock script, persists via systemd)

## /etc/tuned/ppd.conf (belt-and-suspenders mapping)

```ini
[main]
default=desktop
battery_detection=true

[profiles]
power-saver=powersave
balanced=desktop
performance=throughput-performance

[battery]
balanced=balanced-battery
```

This matters IF tuned-ppd is ever unmasked and runs again.

## Coredump

`/etc/systemd/coredump.conf.d/limits.conf`:
```ini
[Coredump]
Storage=external
ProcessSizeMax=512M
ExternalSizeMax=512M
MaxUse=1G
KeepFree=2G
```

## Journald

`/etc/systemd/journald.conf.d/limits.conf`:
```ini
[Journal]
SystemMaxUse=512M
SystemKeepFree=1G
MaxRetentionSec=3month
```

## ZRAM

`/etc/systemd/zram-generator.conf`:
```ini
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
```

Important: the file must be at `/etc/systemd/zram-generator.conf` (NOT `.conf.d/`). The generator
reads this path directly at boot. `/usr/lib/systemd/zram-generator.conf` (Fedora default) provides
fallback; `/etc/` takes precedence but only kicks in on next boot — `zramctl` live output reflects
the running device until then. Do not mistake "not found" messages from a manual generator
invocation for a misconfiguration; those run without the boot-time search path context.

## Weekly cleanup script: system-cleanup.sh

`/usr/local/sbin/system-cleanup.sh` key design choices:

**pipefail isolation**: the script uses `set -euo pipefail`. Every section that pipes output
through `| while read ... done` MUST end with `|| true`, otherwise a non-zero exit from the
left side of the pipe (e.g. podman fails due to a locked image) aborts the entire script:
```bash
# WRONG — podman failure aborts subsequent flatpak/tmpfiles/df sections:
sudo -u rainbow bash -c '...' 2>&1 | while read -r l; do log "$l"; done

# CORRECT:
sudo -u rainbow bash -c '...' 2>&1 | while read -r l; do log "$l"; done || true
```
Apply `|| true` to: podman block, both flatpak lines, journal vacuum, tmpfiles, df, and disk report.

**buildah guard** (correct predicate as of Sep 2026):
```bash
# WRONG — checks /var/tmp dir mtime (creation time, not build activity; also catches cache dirs):
RECENT=$(find /var/tmp/buildah* -maxdepth 0 -mmin -60 2>/dev/null | wc -l)

# CORRECT — directly queries buildah storage for active working containers:
BUILDER_LINES=$(buildah containers 2>/dev/null | wc -l)
if [[ "$BUILDER_LINES" -le 1 ]]; then   # 1 = header only = no working containers
    buildah rm --all 2>/dev/null | ...
else
    echo "skipped: $((BUILDER_LINES - 1)) working container(s) present"
fi
```
`buildah containers` (no flags) outputs a header + one line per working container stored in
buildah's own storage. Podman containers do NOT appear here. `wc -l == 1` means header-only = safe.

**flatpak --user scope**: root's `flatpak uninstall --unused` only touches system runtimes.
User runtimes under `~/.local/share/flatpak` require a separate `sudo -u <user> flatpak --user` call:
```bash
flatpak uninstall --unused --noninteractive --system 2>&1 | tail -3 | while read -r l; do log "$l"; done || true
sudo -u rainbow flatpak uninstall --unused --noninteractive --user 2>&1 | tail -3 | while read -r l; do log "$l"; done || true
```
This works from a systemd oneshot (no D-Bus session) and does not remove in-use runtimes (--unused
skips runtimes referenced by installed apps).

## Pending sysctl additions (not yet applied — requires sudo; Sep 2026)

Append to `/etc/sysctl.d/99-desktop-perf.conf`, then run `sudo sysctl --system`:

```
vm.dirty_writeback_centisecs=1500    # default 500 (5s); 1500=15s reduces writeback wakeup spikes on NVMe/btrfs
fs.inotify.max_user_watches=524288   # default 262144; can be silently exhausted by Hyprland+LSP+Hermes+containers
```

Verify after applying:
```bash
sudo sysctl --system 2>&1 | grep -E "dirty_write|inotify.max_user_watches"
# expect: vm.dirty_writeback_centisecs = 1500
# expect: fs.inotify.max_user_watches = 524288
```

Also add these to the sysctl-verify.sh drift check once applied.

## Weekly sysctl drift check: sysctl-verify.sh

Must verify ALL values that are set — including vm.swappiness (easy to omit since it's in a
different file from the other keys):
```bash
check vm.swappiness                 10
check vm.vfs_cache_pressure         35
check vm.compaction_proactiveness   0
check vm.watermark_boost_factor     1
check vm.watermark_scale_factor     125
check fs.inotify.max_user_instances 512
check net.ipv4.tcp_fastopen         1
# add after pending items applied:
# check vm.dirty_writeback_centisecs  1500
# check fs.inotify.max_user_watches   524288
```
If a value is changed (e.g. tcp_fastopen reverted from 3 to 1), update the check immediately
or it becomes a persistent false-positive drift alert.

## Version control for /etc overlays (ostree persistence)

On Silverblue, `/etc` changes persist across `rpm-ostree upgrade` via ostree's 3-way merge.
However, `/usr/local/sbin/` scripts (not ostree-managed) are lost on factory reset or rebase.

Recommended: git repo at `~/system-config/` mirroring all changed files:

```
system-config/
  etc/sysctl.d/
  etc/systemd/system/
  etc/systemd/coredump.conf.d/
  etc/systemd/journald.conf.d/
  etc/systemd/zram-generator.conf.d/    # note: store as .conf.d/<name>.conf; restore.sh flattens
  etc/tuned/
  etc/udev/rules.d/
  usr-local-sbin/                       # NOT /usr/local/sbin/ directly — avoid root-owned git dir
  home-config/hypr/
  home-config/autostart/
  restore.sh
  README.md
```

**restore.sh `$HOME` bug when run as root**: if invoked via `sudo bash restore.sh`, `$HOME=/root`
and home-config files silently land in `/root/.config` instead of the real user's homedir.
Fix:
```bash
if [[ "${EUID:-0}" -eq 0 ]]; then
    TARGET_USER="${SUDO_USER:-rainbow}"
    TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
else
    TARGET_HOME="$HOME"
fi
```
Use `TARGET_HOME` consistently; do not reference `$HOME` after this block.

## bash-language-server wrapper

`~/.hermes/lsp/bin/bash-language-server-wrapped`:
```bash
#!/bin/bash
export NODE_OPTIONS="--max-old-space-size=384"
exec /usr/bin/bash-language-server "$@"
```
384MB: headroom above tree-sitter leak ceiling (~350MB) before SIGABRT; below system-level OOM risk.
200MB was too low (premature GC failures observed).
