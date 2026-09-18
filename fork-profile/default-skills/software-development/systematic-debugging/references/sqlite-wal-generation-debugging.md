# SQLite WAL Generation / DeletedWalGenerationError Debugging

Applies when Hermes (or any SQLite WAL-mode app) logs a "retired WAL generation" or
`DeletedWalGenerationError` and sessions divert to `.jsonl` / `pending_messages/`.

## Symptom pattern

- `state.db-wal` or `state.db-shm` is missing from disk
- One or more processes hold deleted FDs to those inodes (visible as `(deleted)` in lsof output)
- New `state.db.retired-wal-<timestamp>-<pid>/` artifact directories are created on each restart
- The gateway keeps restarting and immediately reproducing the condition

## Diagnostic sequence

### 1. Stop writers
```bash
systemctl --user stop hermes-gateway-fork.service   # or relevant service
ps aux | grep 'hermes.*gateway' | grep -v grep
```

### 2. Check for deleted FD holders across all processes
```bash
for pid in $(ls /proc/ 2>/dev/null | grep '^[0-9]'); do
  result=$(ls -la /proc/$pid/fd/ 2>/dev/null | grep "state.db.*deleted")
  [ -n "$result" ] && echo "PID $pid: $result"
done
echo "Scan done"
```
Kill any remaining holders only after the service is stopped.

### 3. Read all artifact manifests before deleting anything
```bash
for d in ~/.hermes/profiles/*/state.db.retired-wal-*/; do
  echo "=== $d ==="
  cat "$d/manifest.json"
done
```
Key fields: `change_counter`, `wal_bytes`, `mode` (`copied` vs `header_only`).

### 4. Confirm no data is lost
```python
import sqlite3, json, pathlib
live = sqlite3.connect('/var/home/rainbow/.hermes/profiles/fork/state.db')
live_cc = live.execute('PRAGMA schema_version').fetchone()[0]
for mf in pathlib.Path('/var/home/rainbow/.hermes/profiles/fork/').glob('state.db.retired-wal-*/manifest.json'):
    m = json.loads(mf.read_text())
    print(mf.parent.name, 'artifact cc:', m.get('change_counter'), 'live cc:', live_cc,
          'wal_bytes:', m.get('wal_bytes'), 'mode:', m.get('mode'))
```
- `change_counter` in artifact == live DB change_counter: all frames already committed, artifact is forensic only — safe to delete.
- `wal_bytes > 0` AND artifact `change_counter` > live: run `hermes sessions recover --source <artifact>/state.db --inspect-only` before deleting.
- `mode=header_only`: artifact has no copied DB; do not attempt `--source` on it.

### 5. Check the root cause: compile-time vs runtime SQLite version
```bash
# Compile-time (what Python's sqlite3 module reports):
python3 -c "import sqlite3; print('compile-time:', sqlite3.sqlite_version)"

# Runtime (what the shared library actually is):
python3 -c "
import ctypes
lib = ctypes.cdll.LoadLibrary('libsqlite3.so.0')
lib.sqlite3_libversion.restype = ctypes.c_char_p
print('runtime:', lib.sqlite3_libversion().decode())
"
```
If runtime < 3.52.0, the WAL-reset bug is present even if compile-time says otherwise.
`is_sqlite_wal_reset_vulnerable()` reads the compile-time version and will incorrectly
return `False` — WAL mode gets enabled, and each gateway restart triggers the bug.

## Fix

Set `database.journal_mode: delete` in the affected profile's `config.yaml`.
Then, while the DB has no open connections, checkpoint and switch:

```python
import sqlite3
c = sqlite3.connect('/var/home/rainbow/.hermes/profiles/fork/state.db')
assert c.execute('PRAGMA integrity_check').fetchone() == ('ok',)
c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
c.execute('PRAGMA journal_mode=DELETE')
c.close()
```

Restart the service and verify: `ls ~/.hermes/profiles/fork/state.db*` should show only `state.db` (no `-wal` or `-shm`).

## Pitfalls

- **Do not `kill -TERM <pid>` to fix this.** Systemd restarts the gateway immediately; the new process re-triggers the condition before you can intervene. Stop the service unit instead.
- **Do not delete retired-wal dirs without checking change_counter.** They are Hermes's forensic capture of the state at failure time; if `wal_bytes > 0` and the artifact's counter is ahead of the live DB, committed frames need recovery first.
- **Do not confuse the symptom (missing WAL on disk) with the cause.** The WAL is missing because a second connection did a WAL-init TRUNCATE checkpoint, atomically replacing the inode. Any process that had the old inode is now holding a deleted FD.
- **`lsof` on a non-existent path returns nothing.** Use the `/proc/<pid>/fd/` scan — it catches deleted-inode holders that `lsof <path>` misses because the path no longer exists on disk.
- **Compile-time vs runtime SQLite version mismatch.** Python venvs compiled against a newer SQLite may link to an older system `libsqlite3.so.0` at runtime. Always check both versions before trusting `sqlite3.sqlite_version`.
