# wal-guard.sh — Design and Pitfalls

Path: `~/.local/bin/wal-guard.sh`
Invoked as: `ExecStartPre=` in `~/.config/systemd/user/hermes-gateway.service.d/wal-guard.conf`

## Two-pass structure

**Pass 1 — kill `(deleted)` holders**
```bash
PIDS=$(lsof -n -P 2>/dev/null \
  | awk -v db="$DB" '
      $0 ~ db"-wal" && $0 ~ "\\(deleted\\)" { print $2 " " $1 }
      $0 ~ db"-shm" && $0 ~ "\\(deleted\\)" { print $2 " " $1 }
    ' | sort -u)
```

**Pass 2 — kill wrong-generation (inode-mismatch) holders**
```bash
# Only runs if WAL file exists AND stat succeeds (race-guard on both conditions).
if [ -e "$WAL" ]; then
  CURRENT_WAL_INODE=$(stat -c '%i' "$WAL" 2>/dev/null || true)
  CURRENT_SHM_INODE=$(stat -c '%i' "$SHM" 2>/dev/null || true)
  if [ -n "$CURRENT_WAL_INODE" ] && [ -n "$CURRENT_SHM_INODE" ]; then
    # awk: lsof columns with -n -P: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
    # NODE=$(NF-1), NAME=$NF
    STALE_PIDS=$(lsof -n -P 2>/dev/null \
      | awk -v db="$DB" -v wi="$CURRENT_WAL_INODE" -v si="$CURRENT_SHM_INODE" '
          { name=$NF; node=$(NF-1) }
          name ~ db"-wal" && !(name ~ "\\(deleted\\)") && node != wi { print $2 " " $1 }
          name ~ db"-shm" && !(name ~ "\\(deleted\\)") && node != si { print $2 " " $1 }
        ' | sort -u)
    ...
  fi
fi
```

**Verify section**: checks BOTH classes (deleted and inode-mismatch) and logs warnings but does not block gateway start.

## Critical pitfalls

**Empty-inode race**: if the WAL file is deleted between `[ -e "$WAL" ]` and `stat`, `CURRENT_WAL_INODE` is empty. An empty awk variable `wi=""` makes `node != wi` true for ALL open files, killing every process holding the WAL including the newly-started gateway. Guard: `[ -n "$CURRENT_WAL_INODE" ] && [ -n "$CURRENT_SHM_INODE" ]` before running awk. If stat fails, skip Pass 2 entirely (no file = no stale holders possible).

**lsof performance**: bare `lsof` does hostname and port-name resolution, adding ~2s per call. Use `lsof -n -P` (no DNS, no port names) on all calls. Three calls = ~6s saved at gateway startup.

**awk column layout**: lsof output with `-n -P` uses fixed columns: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME. NODE is `$(NF-1)`, NAME is `$NF`. Verify this assumption holds on the live system:
```bash
lsof ~/.hermes/state.db-wal 2>/dev/null | awk 'NR>1{print NF, $(NF-1), $NF}' | head -3
# Expected: 9 <inode> /path/to/state.db-wal
```
If NF != 9 (e.g. extra fields), the column assumption breaks. Use `-F` mode for robustness:
```bash
lsof -F pcn <file>  # p=pid c=command n=filename, one field per line
```

**set -e + arithmetic**: `((N++))` returns exit code 1 when N was 0 (arithmetic result is 0 = false). With `set -e` this exits the script silently. Use `N=$((N+1))` instead.

**Verify section scope**: the verify check must cover BOTH pass classes. A verify that only checks `(deleted)` holders gives a false clean when a Pass 2 (inode-mismatch) holder survived.

## Systemd coupling — required for lifecycle correctness

The wal-guard alone is not sufficient. Without the correct systemd unit coupling, the dashboard survives gateway restart and the guard must kill it on every startup (reactive). The proactive fix:

`hermes-dashboard.service`:
```ini
[Unit]
BindsTo=hermes-gateway.service
After=hermes-gateway.service
```

`hermes-gateway.service.d/dashboard-wants.conf`:
```ini
[Unit]
Wants=hermes-dashboard.service
```

This makes the lifecycle coupled: gateway start → dashboard start; gateway stop → dashboard stop (BindsTo); gateway restart → both restart.

**BindsTo + Restart= interaction**: BindsTo propagation suppresses `Restart=` on the stopped unit. Dashboard with `Restart=always` does NOT loop when stopped via BindsTo. The `Wants=` on the gateway side is what causes it to re-start on the next gateway startup.
