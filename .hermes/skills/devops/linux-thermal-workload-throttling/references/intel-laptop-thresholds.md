# Intel ultrabook example: ThinkPad X1 Carbon Gen 9

Session-derived compact reference for conservative thermal-guard defaults.

Hardware observed
- Model: Lenovo ThinkPad X1 Carbon Gen 9
- CPU: Intel Core i5-1145G7
- OS shape: Fedora Silverblue / Atomic-style user-space friendly workflow

Authoritative vendor facts used
- Intel ARK for i5-1145G7 lists:
  - Tjunction: 100 C
  - Configurable TDP-up: 28 W
  - Configurable TDP-down: 12 W

Live telemetry observed during setup
- Preferred temperature source present: `x86_pkg_temp`
- Typical package temperature while checked: about 63-67 C
- CPU governor already: `powersave`
- `thermald`: installed but inactive
- `TLP`: inactive

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

Rootless action pattern that worked
1. Poll thermal zones every 5 seconds.
2. Prefer `x86_pkg_temp`; otherwise use hottest available CPU-relevant zone.
3. Identify managed heavy processes by allowlist patterns.
4. Protect desktop/session essentials explicitly.
5. `renice` and `ionice` the hottest managed process continuously.
6. At critical temperature, briefly `SIGSTOP` then `SIGCONT` the hottest managed process.
7. Under memory pressure, try unloading Ollama models before pausing generic processes.
8. Run the guard via `systemd --user`.

Verification pattern that produced proof
- Read back config and service files.
- Confirm user service is active.
- Inspect `journalctl --user -u <service>` for polling logs.
- Temporarily lower thresholds and run a one-shot pass to force an action.
- Confirm a log line such as:
  - `critical-temp pause pid=<pid> comm=ollama ...`

Cautions
- Do not freeze compositor/audio/session infrastructure.
- Do not present RAM usage thresholds as hardware temperature limits.
- If system-level tuning is requested later, treat `thermald`, `intel_pstate`, and platform power profiles as a separate escalation step.
