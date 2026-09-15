#!/usr/bin/env python3
"""
hindsight-watchdog.py - Proactive Hindsight health monitor
Runs every 5 minutes via systemd user timer
(~/.config/systemd/user/hindsight-watchdog.timer), NOT Hermes cron.
(Replaced the old hermes cron job of the same name.)

Detects:
  1. Service not active/activating -> attempt start
  2. Port not listening after 120s uptime -> restart (hung startup)
  3. /health non-200 with port open (after retries) -> restart
  4. Embedding provider=local in last boot -> warn (dim mismatch risk)

Design notes:
- Exclusive flock so a 180s recovery wait cannot overlap the next 5m cron.
- Reads only the last 200KB of daemon.log (not the full 16MB+) to avoid
  growing I/O cost as the log expands.
- watchdog.log is rotated at 500KB to prevent unbounded growth.
- PID is fetched once and validated (guard against PID=0 / service-gone race).
- Recovery wait matches TimeoutStartSec (180s), not a shorter 90s guess.
"""
import fcntl
import subprocess
import socket
import sys
import time
import os
import re
from datetime import datetime

LOG = os.path.expanduser("~/.hindsight/watchdog.log")
LOCK_PATH = os.path.expanduser("~/.hindsight/watchdog.lock")
LOG_MAX_BYTES = 500_000   # rotate watchdog.log at 500KB
DAEMON_LOG = os.path.expanduser("~/.hindsight/daemon.log")
DAEMON_LOG_TAIL_BYTES = 200_000  # read only last 200KB of daemon.log
HEALTH_URL = "http://127.0.0.1:9177/health"
HUNG_THRESHOLD_S = 120    # seconds after which port-not-open => hung
RECOVERY_WAIT_S = 180     # match unit TimeoutStartSec
RECOVERY_POLL_S = 5
HEALTH_RETRIES = 3
HEALTH_RETRY_DELAY_S = 2
UP_STATES = frozenset({"active", "activating", "reloading"})
DOWN_STATES = frozenset({"inactive", "failed"})


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [watchdog] {msg}"
    print(line)
    _rotate_log()
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _rotate_log():
    """Truncate watchdog.log when it exceeds LOG_MAX_BYTES."""
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > LOG_MAX_BYTES:
            with open(LOG, "rb") as f:
                f.seek(-LOG_MAX_BYTES // 2, 2)
                tail = f.read()
            with open(LOG, "wb") as f:
                f.write(b"[rotated]\n" + tail)
    except Exception:
        pass  # never let rotation crash the watchdog


def acquire_lock():
    """Non-blocking exclusive lock. Returns fd to keep held, or None."""
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.write(fd, f"{os.getpid()}\n".encode())
        return fd
    except BlockingIOError:
        return None
    except OSError as e:
        print(f"watchdog: lock failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

def port_open():
    try:
        s = socket.create_connection(("127.0.0.1", 9177), timeout=3)
        s.close()
        return True
    except Exception:
        return False


def http_healthy():
    try:
        import urllib.request
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def http_healthy_retry(attempts=HEALTH_RETRIES, delay=HEALTH_RETRY_DELAY_S):
    for i in range(attempts):
        if http_healthy():
            return True
        if i < attempts - 1:
            time.sleep(delay)
    return False


def get_active_state():
    r = subprocess.run(
        ["systemctl", "--user", "show", "hindsight-api.service",
         "--property=ActiveState", "--value"],
        capture_output=True, text=True
    )
    state = (r.stdout or "").strip()
    return state if state else "unknown"


def get_main_pid():
    """Return the current MainPID of the service, or None if unavailable/zero."""
    r = subprocess.run(
        ["systemctl", "--user", "show", "hindsight-api.service",
         "--property=MainPID", "--value"],
        capture_output=True, text=True
    )
    try:
        pid = int((r.stdout or "").strip())
        return pid if pid > 1 else None   # 0 or 1 = not a real process
    except ValueError:
        return None


def get_process_uptime_s(pid):
    """Return how many seconds process <pid> has been running, or None."""
    try:
        r = subprocess.run(
            ["ps", "-o", "etimes=", "-p", str(pid)],
            capture_output=True, text=True
        )
        val = r.stdout.strip()
        if val.isdigit():
            return int(val)
    except Exception:
        pass
    return None


def last_startup_info():
    """
    Check the tail of daemon.log for startup completion and provider.
    Returns (completed: bool|None, info: dict).
    Reads only DAEMON_LOG_TAIL_BYTES to avoid reading the full 16MB+ file.
    """
    try:
        with open(DAEMON_LOG, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            read_bytes = min(DAEMON_LOG_TAIL_BYTES, size)
            if read_bytes == 0:
                return None, {"error": "empty daemon.log"}
            f.seek(-read_bytes, 2)
            tail = f.read().decode("utf-8", errors="replace")

        # Find the last boot marker in the tail
        boots = list(re.finditer(r'hindsight_api\.config - Database', tail))
        if not boots:
            # Boot marker not in tail — fall back to whatever is in the window
            completed = 'Application startup complete' in tail
            prov_match = re.search(r'provider=(openai|local)', tail)
            provider = prov_match.group(1) if prov_match else "?"
            return completed, {"ts": "?", "provider": provider, "note": "boot marker outside tail"}

        last_boot_pos = boots[-1].start()
        last_boot_section = tail[last_boot_pos:]
        completed = 'Application startup complete' in last_boot_section

        ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', tail[last_boot_pos:last_boot_pos+100])
        ts = ts_match.group(1) if ts_match else "?"

        prov_match = re.search(r'provider=(openai|local)', last_boot_section)
        provider = prov_match.group(1) if prov_match else "?"

        return completed, {"ts": ts, "provider": provider}
    except Exception as e:
        return None, {"error": str(e)}


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def wait_until_healthy(timeout_s=RECOVERY_WAIT_S, poll_s=RECOVERY_POLL_S):
    deadline = time.monotonic() + timeout_s
    waited = 0
    while time.monotonic() < deadline:
        time.sleep(poll_s)
        waited += poll_s
        if port_open() and http_healthy():
            return True, waited
    return False, waited


def start_service():
    log("WARNING: service not active - attempting start")
    r = subprocess.run(
        ["systemctl", "--user", "--no-block", "start", "hindsight-api.service"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        log(f"ERROR: start command failed rc={r.returncode} {(r.stderr or '').strip()}")
        return False
    ok, waited = wait_until_healthy()
    if ok:
        log(f"STARTED and healthy after {waited}s")
        return True
    state = get_active_state()
    log(f"ERROR: failed to become healthy after {RECOVERY_WAIT_S}s (ActiveState={state})")
    return False


def restart_service(reason):
    log(f"RESTARTING: {reason}")
    r = subprocess.run(
        ["systemctl", "--user", "--no-block", "restart", "hindsight-api.service"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        log(f"ERROR: restart command failed rc={r.returncode} {(r.stderr or '').strip()}")
        return False
    ok, waited = wait_until_healthy()
    if ok:
        log(f"RECOVERED after {waited}s")
        return True
    log(f"RECOVERY FAILED: port/health not ready after {RECOVERY_WAIT_S}s")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("watchdog: another instance holds the lock - exiting")
        return
    try:
        _main()
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        except OSError:
            pass


def _main():
    log("--- health check ---")

    state = get_active_state()

    # 1. Service in a startable-down state?
    if state in DOWN_STATES:
        if not start_service():
            sys.exit(1)
        state = get_active_state()
    elif state not in UP_STATES:
        log(f"WARNING: unexpected ActiveState={state} - not intervening")
        return

    # 2. Port open? (activating without a bound port is normal during model load)
    if not port_open():
        if state == "activating":
            log("port not yet open, service still activating - waiting for next check")
            return

        pid = get_main_pid()
        if pid is None:
            log("WARNING: port not open and MainPID unavailable - service may be restarting")
            return

        elapsed = get_process_uptime_s(pid)
        if elapsed is None:
            log(f"WARNING: port not open, PID {pid} uptime unknown - may be restarting")
            return

        if elapsed > HUNG_THRESHOLD_S:
            restart_service(f"port not open after {elapsed}s runtime (hung startup, PID={pid})")
        else:
            log(f"port not yet open, process {elapsed}s old (PID={pid}) - within normal model-load window")
        return

    # 3. HTTP health? Retry to avoid a single slow /health bouncing the daemon.
    if not http_healthy_retry():
        restart_service("port open but /health returned non-200 after retries")
        return

    # 4. Check embedding provider
    completed, info = last_startup_info()
    if info and info.get("provider") == "local":
        log("WARNING: daemon started with local embeddings (384d) - "
            "dim mismatch crash on next boot if DB has 1536d. "
            "Fix: set HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai in hermes.env")

    ts = info.get("ts", "?") if info else "?"
    prov = info.get("provider", "?") if info else "?"
    boot = "complete" if completed else ("incomplete" if completed is False else "unknown")
    log(f"OK: port open, healthy, last_boot={ts} provider={prov} startup={boot}")


if __name__ == "__main__":
    main()
