---
name: linux-thermal-workload-throttling
description: "Keep Linux laptops below safe operating temperatures by combining vendor thermal limits, conservative working thresholds, and user-space throttling of heavy processes when rootless or Atomic-safe changes are preferred."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [linux, thermal, throttling, laptop, systemd, user-service, silverblue, ollama]
    related_skills: [verification-before-completion, wayland-session-troubleshooting]
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
  - local model servers (`ollama`)
  - agent runtimes (`hermes`, `python`, `node`)
  - known indexing/inference helpers
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
- Example: stop or unload active Ollama models before killing anything.
- If an `ollama runner` is hot, distinguish between the runner and `ollama serve`: killing only the runner may be temporary because the server can immediately spawn a new runner when another local client keeps calling `/api/chat` or related endpoints.
- Before claiming the heat source is resolved, verify whether `ollama serve` is still receiving requests and decide whether to trace the client or stop the server entirely.

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

## Escalation path

If the rootless guard is insufficient and the user wants stronger cooling, propose these next steps separately because they are system-level changes:
- enable `thermald`
- lower `intel_pstate/max_perf_pct`
- use `powerprofilesctl` or platform-specific balanced/power-saver profile
- platform fan-control or BIOS thermal policy changes if supported

## Deliverables

Create and verify:
- a config file with thresholds
- a runnable script under `~/.local/bin/`
- a `systemd --user` unit
- logs showing status polling and at least one forced throttle action

## Reference material

See `references/intel-laptop-thresholds.md` for a compact example using a ThinkPad X1 Carbon Gen 9 with an Intel i5-1145G7 and conservative threshold choices.
