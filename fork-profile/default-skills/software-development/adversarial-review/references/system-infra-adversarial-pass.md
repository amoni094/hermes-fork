# System/Infra Adversarial Pass Pattern

> Offloaded from SKILL.md body (size > 600 lines). Load on demand via skill_view. Paper metrics and dated incident notes are not timeless — re-verify before citing as current.

## System/Infra Adversarial Pass Pattern (Sep 2026)

When the artifact under review is a set of live system changes (sysctl, systemd units, shell scripts, service disables, kernel tuning) rather than code or docs, apply these discipline rules:

**Scope narrows each round.** Only review changes made SINCE the last reviewed state. Do not re-review changes that a prior subagent already assessed — re-litigating confirmed-OK findings wastes the subagent's budget and dilutes the signal. Tell the subagent explicitly which items are NEW this round.

**Pass live state, not file contents.** Give the subagent exact live values — `sysctl -n`, `systemctl is-enabled`, `rfkill list`, `cat /proc/...` output — not what you think the files say. System state and file content can diverge (e.g. a sysctl applied via `sysctl -w` but not yet persisted, or a `sysctl.d` file overridden by a later-loaded file). Pass both the config content AND confirmed live values so the subagent can verify internal consistency.

**Checker script pitfall: grep matches comment lines as active directives:**
- When writing a programmatic checker for systemd unit files, strip comment lines before
  checking directives. Comment lines can contain directive-looking text (e.g. a comment
  reading `# services WantedBy=suspend.target with no After= run post-resume`) that
  matches a `grep WantedBy` pattern and produces a false HIGH finding.
- Correct approach: strip comments first:
  ```python
  active_lines = [l for l in unit_text.splitlines() if not l.strip().startswith('#')]
  assert any('WantedBy=sleep.target' in l for l in active_lines)
  ```
- Concrete case (Sep 2026): a comment in thermal-tune-resume.service explaining suspend.target
  semantics caused a checker to flag WantedBy=sleep.target as a violation. The fix was not
  in the unit file — it was in the checker. Always verify the checker before declaring a HIGH.

**Fix obvious bugs immediately, don't wait for the report.** If you spot a clear error while collecting evidence (e.g. a verify script checking `tcp_fastopen=3` when the persisted value is `1`), fix it before dispatching the subagent. Mention the fix in the subagent context. This avoids the subagent spending time on an already-resolved finding.

**Pre-empt the subagent while it runs.** Subagent dispatch is non-blocking. Use the wait time to run deterministic checks locally — exec bits, config reads, snap connection graphs, hold values, service states. Fix anything confirmable without reasoning, and record each fix. Pass a pre-emption log to the subagent context so it skips already-fixed items and focuses only on residual findings that require adversarial reasoning. A well-pre-empted subagent finds richer issues because the obvious bugs are already gone.

**Dispatch AFTER all changes are confirmed applied, not concurrently.** When the artifact under review is a set of live system changes that require user interaction (e.g. sudo commands the agent cannot run itself), wait for explicit confirmation that every change is live before dispatching the adversarial subagent. Dispatching during the application window produces stale findings — the subagent reviews a partially-applied state and flags problems that will be resolved by in-flight work. Concrete case (Sep 2026): adversarial subagent was dispatched while the user was still running `sudo` commands to persist TCP sysctl values. The subagent correctly reported the values were missing from the file, but the user was actively adding them — the finding was real at dispatch time and stale by the time the report landed. Wasted a full subagent run on a race condition. Rule: confirm ALL user-executed steps complete before dispatch.

**ExecStartPre sleep compounds with Restart= recovery (MEDIUM class):**
A sleep in `ExecStartPre` runs on EVERY start attempt, including crash restarts. With
`Restart=on-failure` and exponential backoff (`RestartSteps`/`RestartMaxDelaySec`),
each restart attempt pays: RestartSec + sleep + service startup time. At maximum backoff
this can be 300s + 120s + ~2s = 422s per attempt. Check every service that has both
`ExecStartPre=/bin/sleep N` AND `Restart=` — if crash recovery latency matters, the
sleep should be conditioned on uptime: only sleep if `$(awk '{print $1}' /proc/uptime | cut -d. -f1)` < N+buffer. For non-critical daemons where 2-7 min recovery is acceptable, leave as-is but document the tradeoff.

**Give the subagent specific question areas.** Vague prompts produce vague findings. For each change, include 2-4 specific technical questions the subagent should investigate (e.g. "does KERNEL==wwan0 match the actual interface name?", "does FAIL=1 in warn() propagate to the outer scope in bash?"). This focuses the live-system investigation.

**systemd disable vs mask distinction — check every service disable:**
- `systemctl disable` removes the WantedBy symlink (prevents autostart on boot) but leaves D-Bus activation live. If a unit has `BusName=` set, any D-Bus client can activate it at runtime regardless of enable state.
- `systemctl mask` creates `/etc/systemd/system/<unit>.service -> /dev/null`, which blocks ALL activation paths: boot, socket, D-Bus, and manual `systemctl start`.
- For any unit with `Type=dbus` or `BusName=` in its service file: disable alone is insufficient — mask is required to fully deactivate. Check by looking at `/usr/share/dbus-1/system-services/` for matching `.service` files.
- Concrete case (Sep 2026): `tuned-ppd.service` (Type=dbus, BusName=org.freedesktop.UPower.PowerProfiles) was disabled but D-Bus activation path remained live. GDM, portals, or `powerprofilesctl` could resurrect it and override the tuned profile. Fix: `systemctl mask tuned-ppd.service`.

**sysctl file ordering can silently override your values:**
- Files in `/etc/sysctl.d/` are applied in alphanumeric order. A file loaded later wins.
- If you set a value in `99-desktop-perf.conf` but another file (`99-swappiness.conf`) also sets the same key and sorts AFTER it, the latter wins — your change is silently overridden at reboot.
- After adding any sysctl to a `.conf` file, run `sudo sysctl --system 2>&1 | grep <key>` and verify the final applied value comes from YOUR file, not a later one.
- Fix pattern: either rename your file to sort last (e.g. `99-zz-desktop-perf.conf`), or remove the conflicting key from the other file.

**Coredump size limiting: ProcessSizeMax ≠ ExternalSizeMax:**
- `ProcessSizeMax=N` in `coredump.conf.d` controls whether the kernel captures the core at all (truncates stack trace if core > N). It does NOT cap the on-disk file size.
- `ExternalSizeMax=N` caps the on-disk size of each individual core file.
- `MaxUse=N` caps total storage across all stored cores.
- A common mistake: setting only ProcessSizeMax and MaxUse, thinking disk is protected. A single 10GB core will be written to disk in full until MaxUse is hit — if MaxUse=1G and one core is 1G, the first core fills the budget. Set all three.

**thermald D-Bus activation bypasses Before= ordering:**
- `thermald` is `Type=dbus` — D-Bus socket activation can start it before `sysctl-remediate.service` runs, even if `sysctl-remediate.service` has `Before=thermald.service`. The `Before=` ordering only applies when both units start together in the same transaction; D-Bus activation is a separate code path that ignores it.
- Correct fix: add a drop-in to thermald itself that forces `After=sysctl-remediate.service`:
  ```bash
  mkdir -p /etc/systemd/system/thermald.service.d/
  cat > /etc/systemd/system/thermald.service.d/after-sysctl-remediate.conf << 'EOF'
  [Unit]
  After=sysctl-remediate.service systemd-sysctl.service
  EOF
  sudo systemctl daemon-reload
  ```
- This ensures thermald waits for sysctl-remediate regardless of whether it was started by systemd, D-Bus socket activation, or `systemctl start` from another unit.
- Verify: `systemctl cat thermald.service` should show the drop-in's `After=` in the merged output.
- Applies to any `Type=dbus` unit that must run AFTER a config-setting unit. The `Before=` in the setter is always insufficient; the `After=` must be in the waiter.

**Cold subagent dispatch: sudo blocks silently — steer early:**
- When dispatching an independent adversarial subagent to review system files, it will
  inevitably hit system-owned paths (/etc/systemd/system/, /usr/local/bin/) and attempt
  sudo to apply fixes. In a non-TTY subagent context, sudo blocks waiting for a password
  that never comes — the subagent stalls silently with no error in the log.
- Steer the subagent before it hits this: in the dispatch prompt, explicitly state:
  "sudo requires a password and will block. For user-owned files, use write_file directly.
  For system files, write fixed content to /tmp/<name>.fixed, then report the path and
  the install command — the parent session will apply it."
- If steering after the fact: use delegate_task action='steer' with the same message.
  The steer lands on the next tool result and unblocks the subagent.
- Detection: subagent log line count stops growing for 60+ seconds after a terminal tool
  call containing 'sudo install' or 'sudo cp'. That's the sudo-block signature.

**Verification pass: run checks with matching privilege level:**
- When verifying files owned by another user (e.g. `/home/galina/.config/autostart/`), run
  the verification command as that user or via sudo. Running a file-existence check as the
  wrong user produces false "file missing" reports for files that exist but are mode 700/600.
  Common pattern: admin user checking galina's home dir files without sudo — every check
  returns missing, leading to unnecessary re-deployments of files that were never absent.
  Fix: always use `sudo ls`, `sudo stat`, or `sudo cat` when verifying files in another
  user's protected directories.

**systemctl is-active concat bug under set -e:**
- In a script with `set -eo pipefail`, `systemctl is-active svc || echo "unknown"` concatenates both stdout streams when is-active fails. The result is `"failed\nunknown"` (or `"inactive\nunknown"`), and a downstream `case` statement sees the concatenated string — no branch matches, so restart is never triggered.
- Correct approach: capture with `|| true` and check the return value:
  ```bash
  unit_state() {
      local svc="$1"
      systemctl is-active "$svc" 2>/dev/null || true
  }
  state=$(unit_state thermald)
  case "$state" in active) ;; *) systemctl restart thermald ;; esac
  ```
- Concrete case (Sep 2026, service-health-watchdog.sh): `is-active || echo "unknown"` produced `"active\nunknown"` and `"failed\nunknown"` — the restart branch never fired.

**rfkill grep -c exits 1 under set -e, concat destroys count:**
- `rfkill list | grep -c 'blocked: yes'` exits 1 when count is zero. Under `set -e` this terminates the script. The common workaround `COUNT=$(rfkill list | grep -c 'blocked: yes' || echo 0)` concatenates stdout + echo, giving `"0\n0"` — arithmetic on a multi-line string fails.
- Correct approach:
  ```bash
  COUNT=$(rfkill list 2>/dev/null | grep -c 'blocked: yes' || true)
  COUNT=${COUNT:-0}
  ```
- Same pattern applies to any `grep -c` that can return zero matches inside command substitution under `set -e`.

**TAB vs space in sysctl -n multi-value output:**
- `sysctl -n net.ipv4.tcp_rmem` returns `4096\t131072\t33554432` (TAB-separated). A string compare against `"4096 131072 33554432"` (space-separated) always fails — the value looks wrong even when it is correct.
- Correct approach: normalize before comparing:
  ```bash
  normalize() {
      local s="$1"
      s="${s//$'\t'/ }"
      s="${s//$'\n'/ }"
      printf '%s' "$s"
  }
  actual=$(normalize "$(sysctl -n net.ipv4.tcp_rmem)")
  expected=$(normalize "4096 131072 33554432")
  [[ "$actual" == "$expected" ]] && echo OK || echo DRIFT
  ```
- Applies to all multi-field sysctl keys: tcp_rmem, tcp_wmem, tcp_mem.

**EPP nullglob silent pass in for loops:**
- A `for` loop over `/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference` silently does nothing if the glob expands to zero paths (e.g. on non-intel_pstate kernels, or if the path doesn't exist). The script reports "OK EPP = balance_power" without having written anything.
- Correct approach:
  ```bash
  shopt -s nullglob
  EPP_SEEN=0
  for epp_file in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
      echo balance_power > "$epp_file" 2>/dev/null || true
      ((EPP_SEEN++)) || true
  done
  if [[ "$EPP_SEEN" -eq 0 ]]; then
      warn "EPP: no cpu*/cpufreq/energy_performance_preference files found — intel_pstate inactive?"
  fi
  ```
- `((EPP_SEEN++)) || true` is required under `set -e` because post-increment returns exit 1 when RENICED=0.

**journal size parsing: human units K/M/G/T:**
- `journalctl --disk-usage` prints sizes like `466.9M`, `1.2G`. `grep -oP '[0-9]+(\.[0-9]+)?(?=M)'` silently matches nothing when systemd prints GB-scale usage.
- Correct approach using awk:
  ```bash
  journal_usage_mb() {
      awk '
          { if (match($0, /[0-9]+(\.[0-9]+)?[KMGT]/)) {
              t = substr($0, RSTART, RLENGTH)
              n = substr(t, 1, length(t)-1) + 0
              u = substr(t, length(t), 1)
              if (u=="K") print int(n/1024)
              else if (u=="M") print int(n)
              else if (u=="G") print int(n*1024)
              else if (u=="T") print int(n*1024*1024)
          } }'
  }
  usage=$(journalctl --disk-usage 2>/dev/null | journal_usage_mb)
  ```

**buildah rm --all guard — query storage directly, not mtime of /var/tmp dirs:**
- WRONG approach: `RECENT=$(find /var/tmp/buildah* -maxdepth 0 -mmin -60 2>/dev/null | wc -l)` — mtime of the dir reflects creation time, not whether a build is actively running. A long-running build started before the -60 min window won't be caught. Also `/var/tmp/buildah*` includes the cache dir, producing false positives.
- CORRECT approach: query buildah's own storage:
  ```bash
  CONTAINERS=$(buildah containers 2>/dev/null | wc -l)
  if [[ "$CONTAINERS" -gt 1 ]]; then
      echo "skipped buildah rm --all: $((CONTAINERS-1)) working container(s) active"
  else
      buildah rm --all 2>/dev/null
  fi
  ```
  `buildah containers` (no flags) returns only WORKING containers (uncommitted, in-build state). `wc -l > 1` accounts for the header line. An empty result (wc -l = 1) means no active builds; safe to prune.
- Verified Sep 2026 on Fedora Silverblue 44 rootless buildah.

**snap refresh.hold: exit 0 does NOT mean the hold was set — verify explicitly:**
- `sudo snap set system refresh.hold=<RFC3339>` exits 0 even when the hold was silently rejected
  (e.g. snapd.apparmor disabled, snapd in degraded mode, or clock/timezone parsing edge cases).
- Always verify: `sudo snap get system refresh.hold` must return the expected timestamp.
  If it returns "not set" or an empty line, the hold failed despite the zero exit code.
- Pattern:
  ```bash
  sudo snap set system refresh.hold="2026-12-09T00:00:00Z"
  HOLD=$(sudo snap get system refresh 2>/dev/null | grep '"hold"' | grep -oP '"[^"]+Z"' | tr -d '"')
  [[ -z "$HOLD" ]] && echo "WARN: hold not applied" || echo "hold confirmed: $HOLD"
  ```
- Concrete case: hold set with exit 0 but `snap get` showed nothing; required a second `snap set`
  invocation. Always verify with `sudo snap get system refresh` object-form output, not exit code.

**Orphaned snap content-provider snaps after removing the primary app snap:**
- When a snap app is removed (e.g. `snap remove firefox`), content-provider snaps it consumed
  (e.g. `mesa-2404`, `gnome-46-2404`, `gtk-common-themes`) remain installed and still auto-refresh.
  These are not automatically garbage-collected even though they now have zero connections.
- Risk: a remaining GPU content-provider snap (e.g. `mesa-2404`) can still mount under `/snap/`
  and its auto-refresh can disrupt session GPU paths even when the app snap is gone.
- After removing any snap that used `plugs: [gpu-2404, opengl]`, audit remaining snaps:
  ```bash
  snap connections | grep -v '^Interface'  # check for orphaned slots
  snap list                                 # review everything still installed
  ```
  Remove orphans: `sudo snap remove <name> --purge`.

**`set -e` + `((N++))` arithmetic exits silently when N was 0:**
- `((N++))` is arithmetic expansion. When N is 0, `((0))` evaluates to false (exit code 1). Under `set -e` this terminates the script silently mid-run, with no error message. Verification scripts that count results with `((PASS++))` or `((FAIL++))` starting from 0 will exit immediately on the first counter increment.
- Correct approach: use `N=$((N+1))` which is an assignment (always exit 0) rather than arithmetic expansion:
  ```bash
  PASS=0; FAIL=0
  ok()   { echo "  PASS: $*"; PASS=$((PASS+1)); }
  fail() { echo "  FAIL: $*"; FAIL=$((FAIL+1)); }
  ```
- Concrete case (Sep 2026): a verification script using `((PASS++))` appeared to run but exited after the very first ok() call with no output for remaining checks. Symptom: partial output, then silent exit.
- Applies to any bash script with `set -e` that uses `((VAR++))` or `((VAR+=N))`.

**lsof column layout assumption: verify NODE=$(NF-1) before relying on it:**
- Standard `lsof` output columns: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME (9 fields with -n -P). `NODE=$(NF-1)` and `NAME=$NF` in awk is correct for this layout. But column count can vary — extra output modes or different lsof versions add fields.
- Always verify the assumption before deploying awk that uses `$(NF-1)` for NODE:
  ```bash
  lsof -n -P /path/to/file 2>/dev/null | awk 'NR>1{print NF, $(NF-1), $NF}' | head -3
  # Expected: 9 <inode> /path/to/file
  ```
- If NF != 9, use lsof's `-F` structured output mode instead (field-per-line, unambiguous):
  ```bash
  lsof -F pcni /path/to/file  # p=pid c=command n=filename i=inode
  ```
- Applies to any awk script parsing lsof output that uses positional field assumptions.

**Desktop .desktop shortcut must be executable or LXQt prompts on launch:**
- LXQt File Manager / PCManFM-Qt shows "Execute or display?" for `.desktop` files lacking
  the executable bit, even with a valid `Exec=` line. Breaks one-click UX for low-confidence users.
- After writing or copying any `.desktop` to a user Desktop: `sudo chmod +x /home/<user>/Desktop/<name>.desktop`
- Check: `ls -la /home/<user>/Desktop/*.desktop | grep -v 'x'` — any `-rw-r--r--` line is missing the bit.

**flatpak --user scope from a systemd oneshot:**
- `flatpak uninstall --unused` run as root only touches the SYSTEM install (`/var/lib/flatpak`). User flatpaks in `~/.local/share/flatpak` are invisible to root's flatpak.
- To prune user runtimes from a root systemd service: `sudo -u <user> flatpak uninstall --unused --noninteractive --user`.
- This works WITHOUT a D-Bus session when the user has `loginctl enable-linger` set — the user's XDG environment is accessible via `sudo -u` even from a no-PAM-session oneshot context (verified Sep 2026 on Fedora Silverblue 44 with linger=yes).
- Always add `--system` explicitly to the root call too, so both scopes are unambiguous.
