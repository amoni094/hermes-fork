---
name: linux-thermal-workload-throttling
triggers:
  - Linux laptop is overheating or running throttled under sustained workloads
  - CPU temperature is hitting unsafe limits during compilation, ML, or parallel builds
  - User wants to cap CPU/GPU power to keep temperatures below safe thresholds
  - Combining vendor thermal limits with conservative working thresholds to prevent thermal throttle
  - CPU temperatures spike immediately after boot or login before settling
  - Heavy user services (inference daemons, agent runtimes) all start simultaneously at login
description: >
  Use when: Keep Linux laptops below safe operating temperatures by combining vendor thermal limits, conservative working thresholds, and user-space throttling of heavy processes when rootless or Atomic-safe changes are preferred.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [linux, thermal, throttling, laptop, systemd, user-service, silverblue, local-inference]
    related_skills: [verification-before-completion, wayland-session-management]
related_skills:
  - hermes-agent
  - atomic-desktop-app-installation
  - verification-before-completion
  - wayland-session-management
---

# Linux thermal workload throttling

Use this skill when the user asks to:
- keep a laptop cooler under local AI or development workloads
- set safe CPU / memory / temperature thresholds
- throttle or pause heavy user processes when the machine overheats
- implement a rootless or Fedora Atomic / Silverblue-safe thermal control loop

This skill is especially useful when system-wide governors or kernel knobs are unavailable, undesirable, or require privilege the agent does not have.

## Outcome

Produce a working, verified thermal guard that:
1. identifies the actual machine and CPU,
2. grounds thresholds in vendor limits plus conservative operating headroom,
3. monitors live temperature and memory pressure,
4. reduces heat by slowing or briefly pausing selected heavy user processes,
5. persists as a user service when appropriate,
6. is verified with real logs and a forced-threshold test.

## Prerequisites

Gather these first:
- laptop model from `/sys/devices/virtual/dmi/id/`
- CPU model from `lscpu`
- live thermal zones from `/sys/class/thermal/thermal_zone*/`
- memory and swap state from `/proc/meminfo` or `free -h`
- current power/CPU policy state if available:
  - `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`
  - `/sys/devices/system/cpu/intel_pstate/*`
  - `powerprofilesctl get`
  - `systemctl is-active thermald`
  - `systemctl is-active tlp`
- current top CPU / RSS users from `ps`

Do not guess which process is causing heat. Inspect it.

## Threshold selection rule

Separate three concepts clearly:

1. Hardware danger limit
- For Intel mobile CPUs this is often `Tjunction` on Intel ARK.
- This is not the preferred operating threshold; it is the ceiling where firmware/platform throttling becomes urgent.

2. Conservative operating threshold
- Pick a `high` temperature well below Tjunction.
- For modern Intel ultrabook CPUs, a good starting point is often:
  - high: 80-85 C
  - critical: 90-92 C
  - resume/cool target: 75-78 C
- Adjust only if you have model-specific evidence.

3. Memory-pressure threshold
- RAM usage is not a thermal safety limit by itself.
- Use it as a workload proxy because swap pressure and large resident model processes sustain CPU/package heat.
- Good starting points:
  - high memory: 85%
  - critical memory: 92%
  - swap-used trigger: 512 MB or higher depending on system size

## Rootless / Atomic-safe control strategy

When you cannot or should not change system-wide knobs, use a user-space guard in this order:

1. Detect the preferred package temperature sensor.
- Prefer `x86_pkg_temp` when present.
- Otherwise select the hottest relevant CPU package/core sensor.

2. Identify managed heavy processes.
- Match only the classes of workloads likely to be intentionally heavy, for example:
  - local model servers (e.g. `ollama` if installed, or other inference daemons)
  - agent runtimes (`hermes`, `python`, `node`)
  - known indexing/inference helpers
- Before assuming `ollama` is present, verify: `pgrep -x ollama` or `systemctl --user is-active ollama`. As of Jul 2026 Ollama is not installed on this machine — check before targeting it.
- Keep an explicit protected list for desktop/session processes so you do not freeze the UI.

3. Apply low-risk throttling first.
- `renice` the hottest managed process.
- apply `ionice -c 3` where available

4. On critical temperature, briefly pause the hottest managed process.
- `SIGSTOP`
- short sleep
- `SIGCONT`
- add a cooldown window so you do not flap constantly

5. On memory pressure, unload model weights or pause the heaviest managed process.
- Example: if an Ollama model server is running (`pgrep ollama`), stop or unload active models before killing anything.
- If an `ollama runner` is hot, distinguish between the runner and `ollama serve`: killing only the runner may be temporary because the server can immediately spawn a new runner when another local client keeps calling `/api/chat` or related endpoints.
- Before claiming the heat source is resolved, verify whether `ollama serve` is still receiving requests and decide whether to trace the client or stop the server entirely.
- If Ollama is not installed, look for other inference runtimes (vllm, llama.cpp, etc.) as the resident weight holder.

6. Persist with a user `systemd --user` service if the control loop should survive shell exit.

## Process-selection pitfalls

- Never blanket-stop all high-CPU processes.
- Do not target compositor/session essentials like `Hyprland`, `Xwayland`, `pipewire`, browsers in active use, or `systemd` infrastructure.
- Use both CPU% and RSS size so large resident model processes can be de-prioritized even when instantaneous CPU briefly drops.
- Treat inference/model servers specially: unloading an idle-but-resident model can reduce future thermal spikes and memory pressure better than pausing random processes.

## Fedora Atomic / Silverblue guidance

Prefer user-space artifacts first:
- `~/.local/bin/` for scripts
- `~/.config/systemd/user/` for services
- `~/.config/<app>/` for thresholds/config

Do not jump to layered packages or privileged sysfs writes unless the user explicitly wants system-level tuning.

## Verification workflow

Always verify all of these before claiming success:

1. Read back the config file.
2. Read back the user service file.
3. Check `systemctl --user is-active <service>`.
4. Inspect recent journal lines for live polling/logging.
5. Force a safe one-shot test by temporarily lowering thresholds so an action definitely triggers.
6. Restore the real thresholds after the test.
7. Report the exact action observed in logs, such as `critical-temp pause` or model unload.

A thermal guard is not complete just because the script exists. It must run and emit evidence.

## Silverblue / Atomic: EPP + RAPL via system service

On Fedora Silverblue, `/usr` is immutable — you cannot write to `/usr/lib/systemd/system-sleep/` or other base paths. Use `/etc/systemd/system/` for system units (writable on Silverblue).

### EPP + PL1 via thermal-tune.service

Script at `/usr/local/bin/thermal-tune.sh`:
```bash
#!/usr/bin/env bash
# Apply EPP balance_power + RAPL PL1 cap
for f in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
  echo balance_power > "$f" 2>/dev/null || true
done
# Cap PL1 at 28W (i5-1145G7 TDP); adjust for your CPU
PL1_UW=28000000
RADR=/sys/class/powercap/intel-rapl/intel-rapl:0
[ -f "$RADR/constraint_0_power_limit_uw" ] && echo $PL1_UW > "$RADR/constraint_0_power_limit_uw"
```

Unit at `/etc/systemd/system/thermal-tune.service`:
```ini
[Unit]
Description=Apply EPP + RAPL PL1 thermal tuning at boot

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/thermal-tune.sh

[Install]
WantedBy=multi-user.target
```

Key pitfalls:
- ExecStart must point to the INSTALLED binary (`/usr/local/bin/`) not the source stub in `~/.local/bin/`. Keep the home copy as a stub with a comment pointing to the installed path.
- Do NOT add `Before=<user-service>` — systemd does not enforce ordering between system and user units. Remove it.
- `RemainAfterExit=yes` prevents systemd from treating the oneshot as failed after the script exits.

### Persist EPP + RAPL across S3 suspend/resume (Silverblue)

Firmware resets EPP and RAPL constraints on S3 wake. The fix is a `sleep.target`-triggered system service, NOT a `/usr/lib/systemd/system-sleep/` hook (that path is read-only on Silverblue).

`/etc/systemd/system/thermal-tune-resume.service`:
```ini
[Unit]
Description=Re-apply thermal tuning after resume (EPP + PL1 reset on S3)
After=sleep.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/thermal-tune.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=sleep.target
```

Install:
```bash
sudo install -m 644 /path/to/thermal-tune-resume.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable thermal-tune-resume.service
```

Pitfall: `WantedBy=suspend.target` + `After=suspend.target` runs the service when entering suspend, not on resume. Use `sleep.target` only — systemd tears it down after wake, and `After=sleep.target` ensures the service runs post-teardown (i.e., post-resume).

### Soft-throttle for protected processes (renice+ionice, no SIGSTOP)

For processes you cannot SIGSTOP (browsers, active user apps), apply CPU and I/O nice penalties instead:

```python
def softthrottle_candidates(proc_rows, cfg):
    """Renice+ionice heavy browser/chrome processes. Never SIGSTOP."""
    patterns = cfg.get('softthrottle_process_patterns', ['firefox', 'chrome', 'chromium'])
    cpu_threshold = cfg.get('softthrottle_cpu_pct', 30.0)
    throttled = []
    for row in proc_rows:
        if row['cpu_pct'] >= cpu_threshold:
            for pat in patterns:
                if pat in row['name']:
                    renice(row['pid'])  # renice+ionice, no signal
                    throttled.append(row['pid'])
                    break
    return throttled
```

Add keys to config.json so behavior is config-driven, not hardcoded:
```json
{
  "softthrottle_cpu_pct": 30.0,
  "softthrottle_process_patterns": ["firefox", "chrome", "chromium"]
}
```

### Renice idempotency guard

Calling `renice` every poll cycle (e.g. every 3s) is noisy and wasteful. Guard with a `/proc/<pid>/stat` check:

```python
def renice(pid, value=10):
    try:
        # Field 19 (0-indexed 18) in /proc/<pid>/stat is the nice value
        current = int(pathlib.Path(f'/proc/{pid}/stat').read_text().split()[18])
        if current <= value:
            return  # already reniced
    except (FileNotFoundError, ValueError, IndexError):
        return  # process gone
    subprocess.run(['renice', '-n', str(value), '-p', str(pid)], check=False)
    subprocess.run(['ionice', '-c', '3', '-p', str(pid)], check=False)
```

### Verification checklist for system-level thermal changes

```bash
# EPP applied to all cores
cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference  # expect: balance_power

# RAPL PL1 live value
cat /sys/class/powercap/intel-rapl/intel-rapl:0/constraint_0_power_limit_uw  # expect: 28000000

# Services active
systemctl is-active thermal-tune.service
systemctl is-enabled thermal-tune-resume.service

# Verify ExecStart path in unit matches installed binary
grep ExecStart /etc/systemd/system/thermal-tune.service
ls -la /usr/local/bin/thermal-tune.sh
```

### Checker script pitfall: grep comments as directives

When verifying systemd unit files programmatically, strip comment lines before checking directives — comment lines can contain directive-looking text that matches a grep pattern but are not active config. Example false positive: a comment reading `# on resume; services WantedBy=suspend.target ...` will match `grep WantedBy` and produce a false HIGH finding.

Correct approach:
```python
active_lines = [l for l in unit_text.splitlines() if not l.strip().startswith('#')]
assert any('WantedBy=sleep.target' in l for l in active_lines)
```

## Battery charge threshold management (ThinkPad Silverblue)

On Fedora Silverblue, charge thresholds are managed via **systemd hwdb** + a udev rule,
not TLP. TLP is NOT installed on this machine.

### How it works

- `/usr/lib/udev/rules.d/60-upower-battery.rules` fires when a battery device is added
  (boot or hotplug) and reads the hwdb for threshold values.
- `/usr/lib/udev/hwdb.d/*.hwdb` contains a wildcard catch-all entry:
  ```
  battery:*:*:dmi:*
   CHARGE_LIMIT=75,80
  ```
  This sets `charge_control_start_threshold=75` and `charge_control_end_threshold=80`
  for all batteries that don't have a more specific hwdb match.
- The thresholds are written to sysfs at boot; upower reads and exposes them.

### Verify charge threshold is active

```bash
# Quick sysfs check
cat /sys/class/power_supply/BAT*/charge_control_end_threshold    # expect: 80
cat /sys/class/power_supply/BAT*/charge_control_start_threshold  # expect: 75

# Full authoritative status (includes threshold-enabled and threshold-supported fields)
upower -i $(upower -e | grep BAT)
# Look for:
#   charge-start-threshold:        75%
#   charge-end-threshold:          80%
#   charge-threshold-enabled:      yes
#   charge-threshold-supported:    yes
```

### Diagnostic sequence when cap appears broken

1. Check sysfs thresholds (above) — if 80/75 appear, the cap is configured.
2. Check `upower -i` for `charge-threshold-enabled: yes`.
3. Check that the udev rule fired on last boot:
   ```bash
   journalctl -b | grep -i "charge_control\|upower\|battery"
   ```
4. If TLP is suspected: `systemctl is-enabled tlp` / `systemctl is-active tlp` —
   TLP is NOT installed on this machine (returns unit-not-found).
5. If sysfs shows 100 (cap not applied), reload udev rules and trigger manually:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger --subsystem-match=power_supply
   ```

### Pitfall — battery reads ABOVE cap after reboot

The cap prevents *charging above* the end threshold — it does NOT discharge the battery
down to the cap if it is already higher. If the battery was charged to 90% before the
cap was applied (e.g. on the first boot after a fresh OS install), the laptop draws from
the battery but won't charge above 80% when it next plugs in. The reading above 80%
is normal; it resolves once the battery drains below the start threshold (75%) and is
allowed to charge back to 80%.

Consequence: after applying the charge cap for the first time, expect the battery to
read above 80% for the remainder of that discharge cycle. Verify the cap is working by
draining below 75%, then plugging in and confirming it stops at 80%.

### Pitfall — udev rule only fires on device add event

If the rule doesn't fire (e.g. udev restart mid-session, or the rule was installed after
boot), the kernel reverts to its default (100%). The cap is re-applied on next reboot
or via the manual `udevadm trigger` command above.

## Battery power profile management (ThinkPad Silverblue, Sep 2026)

On this machine, `powerprofilesctl` is NOT installed. The power management tool is `tuned-adm`.

**Available profiles relevant to battery use:**
- `desktop` — default; suitable for plugged-in use; does NOT switch automatically on battery
- `balanced-battery` — reduces power draw; correct profile when on AC=0 (unplugged)
- `powersave` — maximum power saving; useful for very low battery
- `balanced` — generic balanced, no battery bias

**Check AC state:**
```bash
cat /sys/class/power_supply/AC*/online   # 1=plugged in, 0=on battery
```

**Switch to battery-appropriate profile when unplugged:**
```bash
sudo tuned-adm profile balanced-battery
tuned-adm active   # verify
```

**Switch back when plugged in:**
```bash
sudo tuned-adm profile desktop
```

**Pitfall — profile does NOT auto-switch on AC change:** Unlike `power-profiles-daemon`
(which integrates with GNOME/KDE for automatic AC detection), tuned does not automatically
switch profiles when you plug/unplug. Profile must be set manually or via a udev rule.

**Automatic switching via udev (optional):**
```bash
# /etc/udev/rules.d/90-tuned-battery.rules
SUBSYSTEM=="power_supply", ATTR{online}=="0", RUN+="/usr/sbin/tuned-adm profile balanced-battery"
SUBSYSTEM=="power_supply", ATTR{online}=="1", RUN+="/usr/sbin/tuned-adm profile desktop"
```
Load with `sudo udevadm control --reload-rules`.

**Battery health context:** At 70% design capacity (observed Sep 2026), maximizing battery
life per charge matters more. Always use `balanced-battery` or `powersave` when unplugged.

**Check battery state quickly:**
```bash
upower -i $(upower -e | grep BAT) | grep -E "state|percentage|energy-rate|capacity:"
```

---

## Reactive throttle: renice a running daemon without restarting it

When a heavy background daemon (inference, embedding, indexing) is already burning CPU
and pushing temps high, renice it live — no restart needed, immediate thermal relief:

```bash
# Identify the offender
ps aux --sort=-%cpu | head -10

# Renice to background priority (nice 19)
PID=$(pgrep -u "$USER" -f 'process-name' | head -1)
renice 19 -p "$PID" && echo "Reniced $PID"

# Verify the drop (allow 5–10s)
sensors | grep Package
```

Observed result on ThinkPad i5-1145G7: `hindsight-api` at 89.5% CPU / 78°C → 61°C
within 3 seconds of `renice 19`. The process keeps working at background priority.

To make it permanent, add to the service unit:
```ini
# In [Service] section:
CPUWeight=20    # default=100; yields to all normal-priority processes
Nice=19         # lowest scheduler priority
```

Then reload and verify:
```bash
systemctl --user daemon-reload
systemctl --user show <service> -p Nice --value    # expect: 19
systemctl --user show <service> -p CPUWeight --value  # expect: 20
```

**CPUWeight vs Nice:** `CPUWeight=20` controls the cgroup weight (how much CPU the service
gets relative to others at the same level). `Nice=19` controls the per-process scheduler
priority. Both together ensure the daemon loses CPU contention at both the cgroup and
scheduler levels. Use both.

**Note:** `renice` applied to a live process is ephemeral — the unit's `Nice=` only applies
from the NEXT start. For immediate effect: renice live, then update the unit for persistence.

## Boot-time thermal spike prevention

On a fresh login, multiple heavy user services starting concurrently (agent runtimes,
inference daemons, indexing) can push package temperature to 95-96C within 60-90 seconds
before the fan control loop catches up. This is distinct from sustained-load overheating
and requires a different fix: staggered startup, not reactive throttling.

### Observed pattern (ThinkPad i5-1145G7, Fedora Silverblue 44)

- Boot + login: load average 9.96 on a 4-core machine (~2.5x overloaded)
- Top offenders at login: multiple `hermes` processes (90%/9%/5% CPU), `hindsight-api`
  (1.3GB RSS, loading CrossEncoder weights), `Hyprland`
- Package hit 96C within ~90s of login; fans maxed at 5076/5042 RPM
- Root cause: `hindsight-api.service` and Hermes session startup all fired simultaneously

### Fix: ExecStartPre sleep delay on heavy inference daemons

Add a sleep as the FIRST `ExecStartPre` in the service unit so the service waits for the
boot burst to subside before loading model weights into RAM:

```ini
# Boot throttle: wait for system to settle before loading model weights.
# Prevents CPU thermal spike at login (package hitting 96C on fresh boot).
ExecStartPre=/bin/sleep 120
ExecStartPre=/path/to/venv/bin/python3 -c "<model preload>"
ExecStart=/path/to/venv/bin/daemon --args
```

Ordering matters: systemd runs multiple `ExecStartPre` lines in sequence. The sleep MUST
appear before the model-preload line, not after it.

Also bump `TimeoutStartSec` to accommodate the delay:

```ini
# sleep_delay + model_load_time + safety_buffer
# e.g. 120s sleep + <2s load + 60s buffer = 300s
TimeoutStartSec=300
```

Pitfall: if `TimeoutStartSec` is left at its original value (e.g. 180s), systemd will
kill the service mid-sleep and the unit will fail to start on every boot.

PITFALL — ExecStartPre sleep fires on EVERY restart, not just boot:
When the service uses `Restart=on-failure`, a crash recovery attempt also runs ALL
`ExecStartPre` commands — including the sleep. Combined with `RestartSec` and the
exponential backoff (`RestartSteps`/`RestartMaxDelaySec`), recovery time compounds:
  - Restart attempt 1: RestartSec(10s) + sleep(120s) + model load(~2s) = ~132s
  - Restart attempt 5: RestartMaxDelaySec(300s) + sleep(120s) + model load(~2s) = ~422s
If crash recovery latency matters, the correct fix is a boot-detection condition —
e.g. a wrapper script that only sleeps if system uptime < 180s — rather than an
unconditional sleep. For non-critical inference daemons where 2-7 min recovery is
acceptable, the unconditional sleep is simpler and safe to leave as-is.

### Verification after applying

```bash
# Confirm sleep line is present and ordered before model-preload
grep -n "^ExecStartPre" ~/.config/systemd/user/<service>.service
# Line numbers: sleep line must have lower number than model-preload line

# Confirm TimeoutStartSec is >= sleep_delay + 60
grep TimeoutStartSec ~/.config/systemd/user/<service>.service

# Confirm unit reloaded cleanly
systemctl --user show <service> --property=LoadError   # expect: LoadError=
systemctl --user is-active <service>                   # expect: active
```

### Choosing the sleep duration

- 60s: safe minimum for fast SSDs and light session startup
- 120s: validated on this ThinkPad; covers Hyprland + multi-hermes + postgres settling
- 180s: conservative choice if other heavy daemons also start at login

Prefer 120s unless you have evidence the boot burst resolves faster.

### Alternative: `After=` ordering between user services

If you control multiple user services, add `After=<lighter-service>.service` in the heavy
service's `[Unit]` block to serialize startup without a fixed sleep. However, this only
works when all services are user-managed and the lighter ones finish quickly. A sleep is
more robust when the heat source is diffuse (many small processes, not one known service).

## Escalation path

If the rootless guard is insufficient and the user wants stronger cooling, propose these next steps separately because they are system-level changes:
- enable `thermald`
- lower `intel_pstate/max_perf_pct`
- use `powerprofilesctl` or platform-specific balanced/power-saver profile
- platform fan-control or BIOS thermal policy changes if supported

## thermald D-Bus activation bypass: drop-in required on the waiter, not just Before= on the setter

`thermald` is `Type=dbus`. D-Bus socket activation can start it before
`sysctl-remediate.service` finishes, bypassing the `Before=thermald.service` directive
in the sysctl service. `Before=` only applies when both units activate in the same
systemd transaction — D-Bus activation is a separate code path that ignores it.

Fix: add a drop-in to thermald that forces `After=sysctl-remediate.service`:
```bash
mkdir -p /etc/systemd/system/thermald.service.d/
cat > /etc/systemd/system/thermald.service.d/after-sysctl-remediate.conf << 'EOF'
[Unit]
After=sysctl-remediate.service systemd-sysctl.service
EOF
sudo systemctl daemon-reload
```

Verify: `systemctl cat thermald.service` shows the drop-in's After= in merged output.

General rule: for any `Type=dbus` unit that must wait for a config-setter unit, the
`After=` must be in the WAITER's drop-in, not `Before=` in the setter. The setter's
`Before=` cannot control D-Bus-activated starts.

## thermald on ThinkPads: correct drop-in flags

thermald is `Type=dbus` — it must register on D-Bus to signal readiness to systemd.

WRONG (times out): `--no-daemon --ignore-cpuid-check`
  This skips --dbus-enable so systemd never gets the ready signal and kills the process after the start timeout.

CORRECT: preserve the original flags, add only `--ignore-cpuid-check`:
```
mkdir -p /etc/systemd/system/thermald.service.d/
cat > /etc/systemd/system/thermald.service.d/ignore-cpuid.conf << EOF
[Service]
ExecStart=
ExecStart=/usr/bin/thermald --systemd --dbus-enable --adaptive --ignore-cpuid-check
EOF
sudo systemctl daemon-reload && sudo systemctl restart thermald
```
Verify: `systemctl status thermald` → `active (running)`, journal shows `Polling mode is enabled`.

## tuned-adm verify false alarm on intel_pstate

`tuned-adm verify` reports FAILED on `boost` for all intel_pstate machines.
This is a tuned bug: it checks `/sys/devices/system/cpu/cpufreq/boost` which doesn’t exist on intel_pstate.
All real settings (governor, EPP, energy_perf_bias) will show passed.
Turbo state is controlled via `/sys/devices/system/cpu/intel_pstate/no_turbo`.
Ignore the boost failure if no_turbo=0 and EPP=balance_performance are confirmed.

## intel_pstate governor note

powersave governor + intel_pstate is CORRECT on Tiger Lake and other intel_pstate machines.
Do NOT switch to schedutil — that is the correct governor for acpi-cpufreq systems, not intel_pstate.
With intel_pstate active, powersave + HWP gives the hardware full autonomy to boost within EPP guidance.

## Deliverables

Create and verify:
- a config file with thresholds
- a runnable script under `~/.local/bin/`
- a `systemd --user` unit
- logs showing status polling and at least one forced throttle action

## Fedora Silverblue desktop kernel / service tuning (Sep 2026)

The following values and patterns were validated on ThinkPad i5-1145G7 / Fedora Silverblue 44 / 32GB RAM. Adapt conservatively to other hardware — always read live state before applying.

### Validated sysctl values for a 32GB desktop/laptop

Persist in `/etc/sysctl.d/99-desktop-perf.conf`:

```
vm.vfs_cache_pressure=35         # default 100; lower = keep more dentries/inodes hot
fs.inotify.max_user_instances=512  # default 128; needed for Hermes+LSP+containers
net.ipv4.tcp_fastopen=1          # client-side TFO only; 3=server too (unnecessary for desktop)
vm.compaction_proactiveness=0    # default 20; disable if compact_stall > 0 and compact_success = 0
vm.watermark_boost_factor=1      # default 15000; 1 = limit fragmentation-triggered reclaim
vm.watermark_scale_factor=125    # default 10; widens reclaim gap, less kswapd thrash on 32GB
```

**`sysctl -w` is ephemeral — always persist to `/etc/sysctl.d/`:**
Setting a sysctl live via `sysctl -w key=value` takes effect immediately but does NOT survive reboot. Values revert to kernel defaults on next boot. To persist:
- Write to `/etc/sysctl.d/99-desktop-perf.conf` (or another file named 90+ to sort after system defaults in `/usr/lib/sysctl.d/`)
- Reload live without reboot: `sudo sysctl --system` (or `sudo sysctl --load /etc/sysctl.d/99-desktop-perf.conf`)
- On Fedora Atomic/Silverblue: `/etc/sysctl.d/` persists across `rpm-ostree` upgrades; `/usr/lib/sysctl.d/` is replaced by upgrades — only use `/etc/`
- After adding entries, verify the right file wins: `sudo sysctl --system 2>&1 | grep <key>` and confirm the source shows your file, not a later-sorted one

Concrete case (Sep 2026): `net.core.rmem_max` was set live at 32MB in a prior session via `sysctl -w`. On reboot it reverted to the kernel default (4MB) because the value was never written to any `.conf` file. Diagnosis: `sysctl net.core.rmem_max` returned 4194304 post-reboot despite the prior session confirming 33554432. Check that each key is set by only ONE file: run `sudo sysctl --system 2>&1 | grep <key>` and confirm your file wins (not a later-sorted one).

Do not apply `watermark_scale_factor=125` on systems with < 8GB RAM — the absolute watermark headroom is too small and can stall the OOM killer during large allocs.

### Services safe to disable on a single-GPU non-printer ThinkPad

```bash
sudo systemctl disable --now cups.service cups.socket cups.path  # no printers
sudo systemctl disable --now ModemManager.service               # only if modem unused
sudo systemctl disable --now switcheroo-control.service         # single GPU only
```

For WWAN modules (e.g. Quectel EM120R-GL) with ModemManager disabled: block the radio to prevent idle power draw:
```bash
sudo rfkill block wwan
echo 0 | sudo tee /sys/devices/platform/thinkpad_acpi/wwan_enable
# Persist across reboot via udev (thinkpad_acpi wwan_enable is sysfs-ephemeral):
echo 'ACTION=="add", SUBSYSTEM=="net", KERNEL=="wwan0", RUN+="/usr/sbin/rfkill block wwan"' \
  | sudo tee /etc/udev/rules.d/70-wwan-disable.rules
```
systemd-rfkill.service persists the rfkill soft-block state itself; the udev rule is a belt-and-suspenders re-apply on hotplug. The wwan0 interface name is correct for Quectel EM120R-GL via the mhi/wwan kernel driver — it does not get a renamed wwp* name.

### tuned profile: desktop (not balanced)

`tuned-adm profile desktop` adds `kernel.sched_autogroup_enabled=1` on top of `balanced`. This improves latency for interactive desktop use by grouping per-session tasks.

**PPD split-brain fix**: if `tuned-ppd.service` is also installed (it often is on Fedora), it provides a D-Bus translation layer (org.freedesktop.UPower.PowerProfiles) and can override tuned's profile on AC/battery transitions.

Correct fix — mask (not just disable) tuned-ppd, then wire ppd.conf:
```bash
sudo systemctl mask tuned-ppd.service   # disable alone leaves D-Bus activation live
```
Then update `/etc/tuned/ppd.conf` so that IF PPD ever runs (e.g. after unmasking), it maps correctly:
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

### Journal and coredump caps

`/etc/systemd/journald.conf.d/limits.conf`:
```ini
[Journal]
SystemMaxUse=512M
SystemKeepFree=1G
MaxRetentionSec=3month
```

`/etc/systemd/coredump.conf.d/limits.conf`:
```ini
[Coredump]
Storage=external
ProcessSizeMax=512M    # truncates stack trace above this; does NOT cap on-disk size
ExternalSizeMax=512M   # actual per-file on-disk cap
MaxUse=1G
KeepFree=2G
```
Both ProcessSizeMax AND ExternalSizeMax must be set — they control different things (see adversarial-review pitfall).

### ZRAM on Silverblue

`/etc/systemd/zram-generator.conf`:
```ini
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
```
`zstd` gives better compression ratio than the default `lzo-rle` at comparable CPU cost. Takes effect on reboot. Verify with `zramctl` post-reboot.

### Compaction proactiveness check before disabling

Before setting `vm.compaction_proactiveness=0`, verify it's actually failing:
```bash
grep compact /proc/vmstat  # compact_stall > 0 and compact_success = 0 = 100% failure rate
```
If compact_success is non-zero, proactive compaction is working and should be left at its default (20). Disabling it when it's working removes background defragmentation and can increase future allocation latency.

## Live system audit: what to check when diagnosing boot spikes

Run this block to get a complete snapshot before deciding what to change:

```bash
# Thermal + policy
sensors
powerprofilesctl get 2>/dev/null || echo "ppd not running"
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference
cat /sys/devices/system/cpu/intel_pstate/no_turbo
cat /sys/class/powercap/intel-rapl/intel-rapl:0/constraint_0_power_limit_uw

# Memory
free -h
zramctl
sysctl vm.swappiness vm.vfs_cache_pressure vm.dirty_ratio vm.compaction_proactiveness \
       vm.watermark_scale_factor vm.watermark_boost_factor vm.dirty_writeback_centisecs
grep compact /proc/vmstat   # all zeros = compaction_proactiveness=0 is safe

# THP — check both anon and shmem policies
cat /sys/kernel/mm/transparent_hugepage/enabled
cat /sys/kernel/mm/transparent_hugepage/shmem_enabled
grep -E "AnonHugePages|ShmemHugePages" /proc/meminfo

# Process heat sources
ps aux --sort=-%cpu | head -15
ps aux --sort=-%mem | head -10
pgrep -c node   # count node workers; each ~360MB RSS on this machine

# inotify headroom
sysctl fs.inotify.max_user_instances fs.inotify.max_user_watches
```

### Findings from Sep 2026 ThinkPad i5-1145G7 audit

- **THP shmem=never** is correct for this workload. Python/Node allocations are too small to
  benefit from THP; `ShmemHugePages` showed kernel already using 2MB pages via khugepaged
  for large shmem regions. Leave `madvise` for anon, `never` for shmem.
- **compaction all-zero** in /proc/vmstat: `compaction_proactiveness=0` is validated safe
  (no compaction activity at all, so disabling it costs nothing).
- **Node worker pool**: 12 Node.js workers (Hermes news/queue/NUQ/reconciler) each ~355-370MB
  RSS, ~22GB VSZ (V8 address space reservation, not real). Total real RAM ~4.3GB.
  They compete at nice=0 with interactive sessions during boot bursts.
- **irqbalance**: NET_RX imbalance on CPU5 (38k vs 3-6k on others) is expected — VPN tunnel
  concentrates interrupts on one core. Not a problem to fix.
- **dirty_writeback_centisecs=500** (5s default): frequent writeback wakeup causes periodic
  mini-spikes on NVMe/btrfs. Safe to extend to 1500 (15s) — btrfs CoW + ZRAM absorb pressure.
- **fs.inotify.max_user_watches=271996**: can be silently exhausted by Hyprland + LSP +
  Hermes + containers. Bump to 524288.

### Pending sysctl additions (apply with sudo when available)

Append to `/etc/sysctl.d/99-desktop-perf.conf`:

```
# Reduce dirty writeback frequency — 5s default causes periodic mini-spikes on NVMe/btrfs.
# 15s batches writes better; btrfs CoW + ZRAM make this safe.
vm.dirty_writeback_centisecs=1500

# Bump inotify watch limit — 262144 can be silently exhausted by
# Hyprland + LSP + Hermes + containers watching source trees.
fs.inotify.max_user_watches=524288
```

Apply live without reboot:
```bash
sudo sysctl --system 2>&1 | grep -E "dirty_write|inotify.max_user_watches"
```

### Node worker pool renice (implemented Sep 2026)

Hermes runs 12+ Node.js workers at nice=0. During boot bursts they compete with inference
daemons and terminals. The thermoguard already has `node` in `managed_process_patterns` so
it will renice individual hot workers reactively. A proactive oneshot user service renices
the specific worker processes 5 seconds after login.

Verified pattern (~/.config/systemd/user/renice-hermes-workers.service):
```ini
[Unit]
Description=Renice Hermes Node.js background workers after login
After=default.target
After=hermes-gateway.service news-dashboard.service

[Service]
Type=oneshot
ExecStart=/var/home/rainbow/.local/bin/renice-hermes-workers.sh
StandardOutput=journal
StandardError=journal
Restart=no

[Install]
WantedBy=default.target
```

Script (~/.local/bin/renice-hermes-workers.sh):
```bash
#!/usr/bin/env bash
set -euo pipefail
NICE_VALUE=7
LOG="$HOME/.local/state/renice-workers.log"
mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }
log "starting renice pass (nice=$NICE_VALUE)"
sleep 5
RENICED=0
while read -r pid args; do
    if echo "$args" | grep -qE "queue-worker|nuq-worker|extract-worker|reconciler|prefetch|nuq-prefetch"; then
        current_nice=$(awk '{print $19}' /proc/"$pid"/stat 2>/dev/null || echo 0)
        if [[ "$current_nice" -lt "$NICE_VALUE" ]]; then
            renice -n "$NICE_VALUE" -p "$pid" 2>/dev/null && \
                ionice -c 3 -p "$pid" 2>/dev/null && \
                log "reniced pid=$pid nice=$NICE_VALUE ionice=idle args=${args:0:60}" && \
                ((RENICED++)) || true
        else
            log "skipped pid=$pid already nice=$current_nice"
        fi
    fi
done < <(pgrep -u "$USER" -a node 2>/dev/null | awk '{pid=$1; $1=""; print pid, $0}' || true)
log "done: $RENICED workers reniced"
```

Key design points:
- Nice 7 (not 10): workers must stay somewhat responsive for dashboard/gateway use.
- Targets specific worker patterns (queue-worker, nuq-worker, extract-worker, reconciler, prefetch) — does NOT blanket-renice all node processes.
- `((RENICED++)) || true` under `set -e`: post-increment returns exit 1 when RENICED=0; `|| true` prevents premature exit. Works correctly but is a fragile pattern — the count in the log is accurate.
- After= without Wants=: ordering only applies if both units start together. The 5-second sleep is the actual guard.
- thermoguard handles reactive throttling; this service handles the proactive baseline.

PITFALL — After= without Wants= is a weak ordering guarantee:
`After=hermes-gateway.service` only enforces ordering IF hermes-gateway is also starting.
If hermes-gateway isn't enabled or starts at a different point, the renice service fires
immediately after default.target. The 5-second sleep is the actual stabilisation mechanism.

## Container memory policy pitfalls (Sep 2026)

### FalkorDB: use REDIS_ARGS env, not Exec= quadlet override

FalkorDB's container entrypoint is `/var/lib/falkordb/bin/run.sh`, which calls:
```
exec redis-server $REDIS_ARGS --protected-mode no --dir $FALKORDB_DATA_PATH --loadmodule $FALKORDB_BIN_PATH/falkordb.so $FALKORDB_ARGS
```

In a Podman Quadlet `.container` file, `Exec=` replaces the image CMD (the default redis-server invocation) but the ENTRYPOINT (run.sh) still fires. Setting `Exec=redis-server ... --maxmemory` bypasses run.sh's data-dir and loadmodule setup — FalkorDB won't load its graph module.

Correct approach — pass maxmemory via `REDIS_ARGS` environment variable:
```ini
[Container]
Environment=REDIS_ARGS=--maxmemory 1536mb --maxmemory-policy noeviction
Environment=FALKORDB_ARGS=MAX_QUEUED_QUERIES 25 TIMEOUT 1000 RESULTSET_SIZE 10000
```

run.sh expands `$REDIS_ARGS` as the first arguments to redis-server, ahead of its own flags.

### FalkorDB: always noeviction, never allkeys-lru

FalkorDB graph keys (TYPE=graphdata) have TTL=-1 (no expiry, permanent). Using `allkeys-lru` or `allkeys-lfu` will evict active graph nodes mid-query — silent data corruption. Correct policy: `noeviction` with a hard cap. When the cap is hit, clients get an OOM error (visible, recoverable) rather than silently losing graph structure.

Verify key types before setting any eviction policy:
```bash
for key in $(podman exec falkordb redis-cli KEYS "*" 2>/dev/null); do
  ttl=$(podman exec falkordb redis-cli TTL "$key" 2>/dev/null)
  type=$(podman exec falkordb redis-cli TYPE "$key" 2>/dev/null)
  echo "$key: TTL=$ttl TYPE=$type"
done
```

### BullMQ / Firecrawl Redis: volatile-lru, not allkeys-lru

BullMQ stores queue metadata in `bull:{queueName}:meta` keys with TTL=-1 (permanent). These are critical state — evicting them corrupts the queue. Stalled-check heartbeat keys (`bull:{q}:stalled-check`) have short TTLs (20-30s) and are safe to evict.

Correct policy: `volatile-lru` — only evict keys that have a TTL set. The meta keys are protected because they have no TTL.

```yaml
# docker-compose.yaml — Firecrawl Redis
command: redis-server --bind 0.0.0.0 --maxmemory 512mb --maxmemory-policy volatile-lru
```

Do NOT use `allkeys-lru` for any Redis instance that hosts BullMQ queues.

## Reference material

See `references/intel-laptop-thresholds.md` for threshold choices and `references/silverblue-desktop-tuning.md` for the full Sep 2026 validated sysctl/service configuration.

See `references/hermes-cron-offload-classification.md` for the three-tier classification of which Hermes cron jobs can be safely offloaded to native systemd timers vs which must stay in Hermes (LLM/CLI/state.db dependency rules, anti-duplication checks, pause-not-delete discipline).

## Bash scripting correctness: pitfalls in health-check and watchdog scripts

These bugs emerge consistently when writing set -eo pipefail health-check scripts for
watchdog/maintenance timers. Treat as a checklist before deploying any new watchdog unit.

**systemctl is-active concat under set -e:**
NEVER use `STATE=$(systemctl is-active svc || echo unknown)`. Under `set -e`, the
failing is-active writes its output AND the echo fires — STATE becomes `"inactive\nunknown"`.
case/if on a multi-line string never matches any single-line branch.
Correct: `STATE=$(systemctl is-active svc 2>/dev/null || true)` then `${STATE:-unknown}`.

**grep -c zero-count exits 1 under set -e:**
`COUNT=$(cmd | grep -c pattern)` kills the script when count=0 because grep -c exits 1
when no lines match. `|| echo 0` makes it worse: concatenates `"0\n0"`.
Correct: `COUNT=$(cmd | grep -c pattern || true); COUNT=${COUNT:-0}`.

**sysctl -n multi-value output is TAB-separated:**
`sysctl -n net.ipv4.tcp_rmem` returns `4096\t131072\t33554432`. String compare against
space-separated expected always fails. Always normalize both sides before comparing:
`actual=${actual//$'\t'/ }; expected=${expected//$'\t'/ }`

**EPP for-loop over glob silently does nothing when paths don't exist:**
`for f in /sys/.../cpu*/cpufreq/energy_performance_preference` does zero iterations if
the glob matches nothing (default shell behavior). The loop body never runs but no error
is raised. Fix: `shopt -s nullglob` + a counter `EPP_SEEN=0; ((EPP_SEEN++)) || true`
and `[[ $EPP_SEEN -eq 0 ]] && warn "EPP paths not found"` after the loop.

**`((COUNTER++)) || true` required when COUNTER starts at 0 under set -e:**
Post-increment `((N++))` returns exit code 1 when N is 0 (because the result of the
expression is 0, which is falsy in bash). Under `set -e` this terminates the script.
Always write `((N++)) || true` in health-check scripts that count things.

**journal size parsing must handle K/M/G/T units:**
`journalctl --disk-usage` can print `466.9M`, `1.2G`, or (on busy servers) `1.1T`.
`grep -oP '[0-9]+(?=M)'` silently returns nothing for G/T scale values, and the
subsequent arithmetic comparison against a threshold produces a false-OK result.
Use an awk parser that normalizes all units to MB before the comparison.
