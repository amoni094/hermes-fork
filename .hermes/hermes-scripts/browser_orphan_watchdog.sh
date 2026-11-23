#!/usr/bin/env bash
# browser_orphan_watchdog.sh
#
# Watchdog/cleaner for orphaned agent-browser Chrome sessions.
#
# Root cause (confirmed 2026-07-07): when the Hermes process holding a
# browser_tool session is killed outside its normal shutdown path (SIGKILL,
# crash, gateway restart), the in-memory _active_sessions tracking is lost
# but the node + Chromium process tree (main/zygote/gpu/network/storage/
# renderer) keeps running under /tmp/agent-browser-chrome-<session>. These
# only get swept by _reap_orphaned_browser_sessions(), which normally runs
# once at startup and via atexit in a *new* Hermes process — so if no new
# session starts for a while, orphans accumulate silently (122 procs / 10
# sessions were found accumulated from a single afternoon on 2026-07-07).
#
# This script re-runs that exact safe reaper (owner_pid liveness checked,
# won't touch daemons owned by other live Hermes processes) out-of-band on
# a schedule, then falls back to a bounded pgrep+pkill sweep only if a large
# process count remains stuck (defensive net, not primary path).
#
# Designed for cron no_agent=True: silent (no stdout) when nothing to do,
# prints a short report only when it took action or found something stuck.

set -uo pipefail

HERMES_AGENT_DIR="${HERMES_AGENT_DIR:-/var/home/rainbow/.hermes/hermes-agent}"
VENV_PY="${HERMES_AGENT_DIR}/venv/bin/python3"
PATTERN='agent-browser-chrome-'
ALERT_THRESHOLD="${BROWSER_WATCHDOG_ALERT_THRESHOLD:-50}"

count_orphans() {
    pgrep -f "$PATTERN" 2>/dev/null | wc -l
}

before=$(count_orphans)

# Nothing running at all — silent, fast exit.
if [ "$before" -eq 0 ]; then
    exit 0
fi

reap_output=""
reap_ok=0
if [ -x "$VENV_PY" ] && [ -d "$HERMES_AGENT_DIR" ]; then
    reap_output=$(cd "$HERMES_AGENT_DIR" && "$VENV_PY" -c "
import sys, os
sys.path.insert(0, os.getcwd())
try:
    from tools import browser_tool
    result = browser_tool._reap_orphaned_browser_sessions()
    print('reaper_ran ok result=%r' % (result,))
except Exception as e:
    print('reaper_error: %s' % e)
" 2>&1)
    reap_ok=1
fi

after=$(count_orphans)

# Defensive net: reaper is owner-checked and conservative by design, so a
# large stuck count that survives it is unusual. Only intervene directly if
# it's well past a sane threshold, and only with graceful SIGTERM (never -9).
force_killed=0
if [ "$after" -ge "$ALERT_THRESHOLD" ]; then
    pkill -TERM -f "$PATTERN" 2>/dev/null || true
    sleep 2
    force_killed=1
fi

final=$(count_orphans)

# Silent if the reaper alone brought things to zero (or near-zero, i.e. a
# couple of processes belonging to a genuinely active session) and no forced
# kill was needed — that's the reaper working as designed, nothing to alert.
if [ "$force_killed" -eq 0 ] && [ "$final" -le 2 ]; then
    exit 0
fi

echo "browser-orphan-watchdog: before=$before after_reap=$after after_forced_term=$final threshold=$ALERT_THRESHOLD forced_term=$force_killed"
if [ -n "$reap_output" ]; then
    echo "reaper: $reap_output"
fi
if [ "$final" -gt 2 ]; then
    echo "WARNING: $final agent-browser-chrome process(es) still present after cleanup attempts. Manual check recommended: pgrep -fa '$PATTERN'"
fi
exit 0
