# Intel ultrabook example: ThinkPad i5-1145G7 (Tiger Lake)

Session-derived compact reference for conservative thermal-guard defaults.

Hardware observed
- CPU: Intel Core i5-1145G7 (Tiger Lake, 4C/8T, max 4.4GHz, Iris Xe)
- OS: Fedora Silverblue 44
- RAM: 32GB, 11GB used at idle; 8GB zRAM
- Storage: Samsung PM981a NVMe 512GB (btrfs, zstd:1 compression, ssd mode, discard=async)

Authoritative vendor facts used
- Intel ARK for i5-1145G7:
  - Tjunction: 100 C
  - Configurable TDP-up: 28 W
  - Configurable TDP-down: 12 W

Live telemetry observed during setup
- Preferred temperature source present: `x86_pkg_temp`
- Typical package temperature at idle: 57-67 C
- CPU governor: `powersave` (correct for intel_pstate; schedutil is for acpi-cpufreq)
- `intel_pstate`: active, turbo ON (no_turbo=0), min_perf=9%, max_perf=100%
- EPP: balance_performance (set via tuned)
- `thermald`: crashes at boot on stock config — fixed via drop-in (see below)
- `TLP`: not installed
- `tuned`: active; changed to "desktop" profile
- `zRAM`: 8GB, changed to zstd compression
- swappiness=10, vfs_cache_pressure changed to 35
- irqbalance: not installed; lm_sensors: not installed
- btrfs: no autodefrag, space_cache=v2, ssd mode — already optimal

Conservative working thresholds chosen
- `high_temp_c`: 85.0
- `critical_temp_c`: 92.0
- `resume_temp_c`: 78.0
- `mem_high_pct`: 85.0
- `mem_critical_pct`: 92.0
- `swap_high_mb`: 512

Why these values
- 100 C is the silicon/package ceiling, not the desired steady-state target.
- 85 C gives meaningful headroom below hardware thermal emergency behavior.
- 92 C is a stronger intervention point that still stays below Tjunction.
- Memory thresholds are operational heuristics for long-lived AI/dev workloads, not hardware safety limits.

## Optimizations applied (verified working, Fedora Silverblue 44)

In order of actual impact:

1. thermald fixed (--adaptive --ignore-cpuid-check — see below)
2. tuned profile changed: balanced -> desktop
   `sudo tuned-adm profile desktop`
   desktop = balanced + sched_autogroup=1; EPP=balance_performance inherited
3. zRAM compression changed: lzo-rle -> zstd
   Edit /etc/systemd/zram-generator.conf:
   ```
   [zram0]
   zram-size = ram / 2
   compression-algorithm = zstd
   ```
   Takes effect on next boot (systemd-zram-setup@zram0 restart requires device recreation)
4. vm.vfs_cache_pressure lowered: 60 -> 35
   echo 'vm.vfs_cache_pressure=35' | sudo tee /etc/sysctl.d/99-desktop-perf.conf
   sudo sysctl -p /etc/sysctl.d/99-desktop-perf.conf
5. lm_sensors + irqbalance installed (staged via rpm-ostree for next boot)
   rpm-ostree install --idempotent lm_sensors irqbalance
   After boot: sudo sensors-detect; then `sensors` shows per-core temps

Items confirmed OK, no action needed:
- Battery thresholds already set (75/80)
- NVMe scheduler = none (correct for modern NVMe; kernel handles queue)
- btrfs: compress=zstd:1, ssd, discard=async, space_cache=v2, no autodefrag — optimal
- Transparent hugepages = madvise (correct for desktop)
- CPU governor powersave + intel_pstate is correct (NOT schedutil — that's for acpi-cpufreq only)
- systemd-oomd running — no earlyoom needed
- microcode 0xbe — current for this stepping
- fstrim.timer enabled (weekly TRIM)
- swappiness=10 good for high-RAM desktop

## ThinkPad-specific pitfalls

### thermald crashes on boot — correct fix
On ThinkPads with `thinkpad_acpi`, stock thermald exits immediately with:
  `[/sys/devices/platform/thinkpad_acpi/dytc_lapmode] present: Thermald can't run on this platform`

The service is Type=dbus — it must register on D-Bus to signal readiness.
WRONG fix (times out): `--no-daemon --ignore-cpuid-check` (forgets --dbus-enable; systemd never gets ready signal)
CORRECT fix: preserve original flags, add only --ignore-cpuid-check:

```
mkdir -p /etc/systemd/system/thermald.service.d/
cat > /etc/systemd/system/thermald.service.d/ignore-cpuid.conf << EOF
[Service]
ExecStart=
ExecStart=/usr/bin/thermald --systemd --dbus-enable --adaptive --ignore-cpuid-check
EOF
sudo systemctl daemon-reload && sudo systemctl restart thermald
```

Verify: `systemctl status thermald` should show `active (running)` with `Polling mode is enabled`.

### tuned verify false alarm
`tuned-adm verify` reports FAILED on boost for intel_pstate systems. This is a tuned bug:
- Tuned checks `/sys/devices/system/cpu/cpufreq/boost` which doesn't exist on intel_pstate machines
- intel_pstate uses `/sys/devices/system/cpu/intel_pstate/no_turbo` instead
- All real settings (governor, EPP, energy_perf_bias) pass verification
- Turbo is actually ON (no_turbo=0) — ignore this warning

### dytc_lapmode — read-only
`/sys/devices/platform/thinkpad_acpi/dytc_lapmode` = 1 means "lap detection" is active.
This node is READ-ONLY (permissions: r--r--r--). Cannot be forced to 0 via sysfs.
Setting platform_profile=performance does NOT change it.
It is set by the kernel/firmware based on accelerometer/physical orientation.
Leave it; it does not block turbo or cause measurable throttling in practice on this machine.

### Battery charge thresholds
ThinkPads expose charge threshold control via:
  `/sys/class/power_supply/BAT0/charge_control_start_threshold`
  `/sys/class/power_supply/BAT0/charge_control_end_threshold`
Good longevity setting (this machine): start=75, stop=80. Already configured.

### Fan speed exposure
`/sys/devices/platform/thinkpad_acpi/fan_speed_rpm` readable. `lm_sensors` + `thinkpad_acpi` needed for richer data.

## Power tuning quick-audit checklist for this machine

Run these in order when setting up a new boot:
1. `tuned-adm active` — should say desktop
2. `cat /sys/devices/system/cpu/intel_pstate/no_turbo` — should be 0
3. `cat /sys/devices/system/cpu/cpufreq/policy0/energy_performance_preference` — should be balance_performance
4. `systemctl status thermald` — should be active (running)
5. `sysctl vm.vfs_cache_pressure` — should be 35
6. `cat /etc/systemd/zram-generator.conf` — should show compression-algorithm=zstd
7. After lm_sensors boot: `sensors` to confirm package temps

## Rootless thermal action pattern (verified)
1. Poll thermal zones every 5 seconds.
2. Prefer `x86_pkg_temp`; otherwise use hottest available CPU-relevant zone.
3. Identify managed heavy processes by allowlist patterns.
4. Protect desktop/session essentials explicitly.
5. `renice` and `ionice` the hottest managed process continuously.
6. At critical temperature, briefly `SIGSTOP` then `SIGCONT` the hottest managed process.
7. Under memory pressure, try unloading inference runtimes before pausing generic processes.
8. Run the guard via `systemd --user`.

## Verification pattern
- Read back config and service files.
- Confirm user service is active.
- Inspect `journalctl --user -u <service>` for polling logs.
- Temporarily lower thresholds and run a one-shot pass to force an action.
- Confirm a log line such as `critical-temp pause pid=<pid> comm=...`

## Cautions
- Do not freeze compositor/audio/session infrastructure.
- Do not present RAM usage thresholds as hardware temperature limits.
- If system-level tuning is requested later, treat `thermald`, `intel_pstate`, and platform power profiles as a separate escalation step.
- ollama: check `pgrep -x ollama` before targeting it — not installed on this machine as of Sep 2026.
